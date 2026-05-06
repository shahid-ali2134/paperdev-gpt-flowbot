from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import read_json, utc_now_iso, write_json_with_backup


class MemoryManager:
    def __init__(self, memory_path: Path) -> None:
        self.memory_path = memory_path
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.memory_path.exists():
            self.save({"selected_topics": []})

    def load(self) -> dict[str, Any]:
        data = read_json(self.memory_path, {"selected_topics": []})
        data.setdefault("selected_topics", [])
        return data

    def save(self, data: dict[str, Any]) -> None:
        data.setdefault("selected_topics", [])
        write_json_with_backup(self.memory_path, data)

    def previous_topics_text(self) -> str:
        topics = self.load().get("selected_topics", [])
        if not topics:
            return "None yet."
        lines = []
        for item in topics:
            title = item.get("title") or "Untitled"
            selected = item.get("selected_topic") or ""
            paper_id = item.get("paper_id") or ""
            lines.append(f"- {paper_id}: {title} | {selected}".strip())
        return "\n".join(lines)

    def record_selected_topic(self, metadata: dict[str, Any]) -> None:
        data = self.load()
        paper_id = metadata.get("paper_id")
        records = [item for item in data["selected_topics"] if item.get("paper_id") != paper_id]
        records.append(
            {
                "paper_id": paper_id,
                "paper_number": metadata.get("paper_number", 0),
                "month_name": metadata.get("month_name", ""),
                "year": metadata.get("year", 0),
                "title": metadata.get("title", ""),
                "selected_topic": metadata.get("selected_topic", ""),
                "created_at": utc_now_iso(),
                "workspace_path": metadata.get("workspace_path", ""),
            }
        )
        data["selected_topics"] = records
        self.save(data)

    def highest_paper_number_for_month(self, month_name: str, year: int) -> int:
        highest = 0
        for item in self.load().get("selected_topics", []):
            if item.get("month_name") == month_name and item.get("year") == year:
                highest = max(highest, int(item.get("paper_number", 0) or 0))
        return highest
