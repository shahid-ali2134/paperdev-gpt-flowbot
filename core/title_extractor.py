from __future__ import annotations

import re

from core.utils import meaningful_short_text, sanitize_filename_part


TITLE_PREFIXES = (
    "Title:",
    "Paper Title:",
    "Refined IEEE conference-style research title:",
    "IEEE Conference-Style Title:",
    "IEEE-style title:",
    "Refined title:",
    "Research Title:",
)


def clean_markdown(value: str) -> str:
    value = re.sub(r"^[#*\-\s]+", "", value.strip())
    value = value.strip("*_` ")
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .")


def clean_title(value: str) -> str:
    return clean_markdown(value).strip("\"'“”‘’ ")


def extract_title(response: str) -> str:
    lines = [line.strip() for line in response.splitlines() if line.strip()]
    for line in lines:
        plain = clean_markdown(line)
        for prefix in TITLE_PREFIXES:
            if plain.lower().startswith(prefix.lower()):
                title = plain[len(prefix) :].strip(" -:")
                if title:
                    return clean_title(title)
    for index, line in enumerate(lines):
        if "title" in line.lower() and index + 1 < len(lines):
            candidate = clean_title(lines[index + 1])
            if len(candidate.split()) >= 4:
                return candidate
    return clean_title(lines[0]) if lines else "Untitled Research Paper"


def extract_abstract(response: str) -> str:
    heading = (
        r"(?:^|\n)\s*"
        r"(?:[-*#\s]*\d+[\).:-]\s*)?"
        r"(?:\*\*)?"
        r"(?:IEEE[- ]style\s+)?Abstract"
        r"(?:\s+of\s+120[-–]130\s+words\s+only)?"
        r"(?:\*\*)?"
        r"\s*:?\s*"
    )
    stop = (
        r"(?=\n\s*(?:[-*#\s]*\d+[\).:-]\s*)?(?:\*\*)?"
        r"(?:Final novelty|Novelty Points|Final selected dataset|Final Dataset|"
        r"Evaluation Metrics|Dataset|Metrics|Paper Title|Title)"
        r"\b|\Z)"
    )
    match = re.search(
        heading + r"(.*?)" + stop,
        response,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        abstract = clean_markdown(match.group(1).strip())
        abstract = abstract.strip("\"'“”‘’ ")
        return abstract
    return ""


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def short_title(title: str, words: int = 5) -> str:
    return meaningful_short_text(title, words=words)


def generate_chat_name(paper_number: int, month_name: str, title: str) -> str:
    return sanitize_filename_part(f"P{paper_number}{month_name} {short_title(title)}", 90)


def extract_section(response: str, heading: str) -> str:
    pattern = rf"(?:^|\n)\s*(?:[-*#\d. ]*)?(?:\*\*)?{re.escape(heading)}(?:\*\*)?\s*:?\s*(.*?)(?=\n\s*(?:[-*#\d. ]*)?(?:Final novelty|Novelty Points|Final selected dataset|Final Dataset|Evaluation Metrics|Metrics|Title|Abstract)\b|\Z)"
    match = re.search(pattern, response, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def build_clean_final_file(response: str) -> tuple[str, str, str, int]:
    title = extract_title(response)
    abstract = extract_abstract(response)
    abstract_word_count = count_words(abstract)
    content = f"Paper Title : {title}\n\nAbstract:\n{abstract}\n"
    return content, title, abstract, abstract_word_count
