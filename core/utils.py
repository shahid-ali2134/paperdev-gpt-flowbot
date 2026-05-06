from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


WINDOWS_RESERVED_CHARS = r'<>:"/\|?*'


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def sanitize_filename_part(value: str, max_length: int = 80) -> str:
    cleaned = re.sub(f"[{re.escape(WINDOWS_RESERVED_CHARS)}]", " ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:max_length].strip(" .") or "Untitled"


def meaningful_short_text(value: str, words: int = 5) -> str:
    filler = {
        "a",
        "an",
        "and",
        "for",
        "in",
        "of",
        "on",
        "the",
        "to",
        "using",
        "with",
        "based",
        "toward",
        "towards",
        "novel",
        "method",
        "approach",
        "framework",
        "research",
        "paper",
    }
    tokens = re.findall(r"[A-Za-z0-9]+", value)
    selected = [token for token in tokens if token.lower() not in filler]
    if len(selected) < 3:
        selected = tokens
    return sanitize_filename_part(" ".join(selected[:words]), 70)


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    parent = path.parent
    stem = path.name
    index = 2
    while True:
        candidate = parent / f"{stem} - {index}"
        if not candidate.exists():
            return candidate
        index += 1


def backup_if_exists(path: Path) -> Path | None:
    if not path.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.stem}.{timestamp}.bak{path.suffix}")
    shutil.copy2(path, backup)
    return backup


def write_text_with_backup(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_if_exists(path)
    path.write_text(content, encoding="utf-8")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup_if_exists(path)
        return default


def write_json_with_backup(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_if_exists(path)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
