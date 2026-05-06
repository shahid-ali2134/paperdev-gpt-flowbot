from __future__ import annotations

import re

from core.title_extractor import clean_markdown


TOPIC_TITLE_PATTERNS = (
    r"(?:IEEE-style suggested title|IEEE-style title|Suggested title|Topic title|Research topic|Title)\s*:\s*(.+)",
    r"^\s*(?:topic\s*)?\d+[\).:-]\s+\*\*(.+?)\*\*",
    r"^\s*(?:topic\s*)?\d+[\).:-]\s+(.+)",
    r"^\s*#+\s*(?:topic\s*)?\d+[\).:-]?\s*(.+)",
)


def extract_first_recommended_topic(response: str) -> str:
    """Extract the first usable topic/title from a ChatGPT topic-discovery response."""
    lines = [line.strip() for line in response.splitlines() if line.strip()]

    marked = extract_marked_first_topic(response)
    if marked:
        return marked

    for line in lines:
        plain = clean_markdown(line)
        for pattern in TOPIC_TITLE_PATTERNS:
            match = re.search(pattern, plain, flags=re.IGNORECASE)
            if match:
                candidate = clean_topic_candidate(match.group(1))
                if is_usable_topic(candidate):
                    return candidate

    raise ValueError("Could not extract the first recommended topic from Prompt 1 response.")


def extract_marked_first_topic(response: str) -> str:
    patterns = (
        r"FIRST_RECOMMENDED_TOPIC\s*:\s*(.+)",
        r"SELECTED_TOPIC\s*:\s*(.+)",
        r"TOPIC_TITLE\s*:\s*(.+)",
    )
    for pattern in patterns:
        match = re.search(pattern, response, flags=re.IGNORECASE)
        if match:
            candidate = clean_topic_candidate(match.group(1))
            if is_usable_topic(candidate):
                return candidate
    return ""


def clean_topic_candidate(value: str) -> str:
    value = clean_markdown(value)
    value = re.sub(r"^\d+[\).:-]\s*", "", value)
    value = value.strip("\"'`*_ -:")
    value = re.sub(r"\s+", " ", value)
    return value


def is_usable_topic(value: str) -> bool:
    if len(value.split()) < 5:
        return False
    lowered = value.lower()
    if len(value) > 180:
        return False
    if lowered.startswith(("good", "great", "sure", "certainly", "based on", "since ", "because ")):
        return False
    rejected_starts = (
        "core idea",
        "why it is novel",
        "possible datasets",
        "colab feasibility",
        "possible contribution",
        "expected evaluation",
        "rank",
        "here are",
    )
    return not lowered.startswith(rejected_starts)
