from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from core.utils import (
    ensure_unique_path,
    meaningful_short_text,
    read_json,
    sanitize_filename_part,
    utc_now_iso,
    write_json_with_backup,
    write_text_with_backup,
)


class PaperWorkspaceManager:
    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root

    @staticmethod
    def current_month_parts(now: datetime | None = None) -> tuple[str, int]:
        current = now or datetime.now()
        return current.strftime("%B"), current.year

    def month_folder(self, month_name: str, year: int) -> Path:
        return self.output_root / f"{month_name} {year} Papers"

    def ensure_month_folder(self, month_name: str, year: int) -> Path:
        folder = self.month_folder(month_name, year)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def next_paper_number(self, month_name: str, year: int, memory_highest: int = 0) -> int:
        folder = self.month_folder(month_name, year)
        highest = memory_highest
        if folder.exists():
            pattern = re.compile(rf"^P(\d+){re.escape(month_name)}\b", re.IGNORECASE)
            for child in folder.iterdir():
                if child.is_dir():
                    match = pattern.match(child.name)
                    if match:
                        highest = max(highest, int(match.group(1)))
        return highest + 1

    def create_workspace(
        self,
        topic_area: str,
        keywords_or_focus: str,
        memory_highest: int = 0,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        month_name, year = self.current_month_parts(now)
        month_folder = self.ensure_month_folder(month_name, year)
        paper_number = self.next_paper_number(month_name, year, memory_highest)
        paper_id = f"P{paper_number}{month_name}"
        topic_hint = meaningful_short_text(f"{topic_area} {keywords_or_focus}", words=5)
        folder_name = sanitize_filename_part(f"{paper_id} {topic_hint}", 100)
        workspace_path = ensure_unique_path(month_folder / folder_name)
        workspace_path.mkdir(parents=True)
        metadata = {
            "paper_id": paper_id,
            "paper_number": paper_number,
            "month_name": month_name,
            "year": year,
            "created_at": utc_now_iso(),
            "month_folder": str(month_folder),
            "workspace_path": str(workspace_path),
            "topic_area": topic_area,
            "keywords_or_focus": keywords_or_focus,
            "selected_topic": "",
            "title": "",
            "abstract": "",
            "abstract_word_count": 0,
            "chat_name": "",
            "chat_url": "",
            "status": "created",
            "files": [],
            "warnings": [],
        }
        self.save_metadata(metadata)
        return metadata

    def metadata_path(self, workspace_path: Path) -> Path:
        return workspace_path / "metadata.json"

    def load_metadata_from_workspace(self, workspace_path: Path) -> dict[str, Any]:
        return read_json(self.metadata_path(workspace_path), {})

    def save_metadata(self, metadata: dict[str, Any]) -> None:
        write_json_with_backup(Path(metadata["workspace_path"]) / "metadata.json", metadata)

    def find_workspace(self, paper_id: str) -> Path:
        matches: list[Path] = []
        if self.output_root.exists():
            for month_folder in self.output_root.glob("* Papers"):
                if month_folder.is_dir():
                    matches.extend(path for path in month_folder.glob(f"{paper_id}*") if path.is_dir())
        if not matches:
            raise FileNotFoundError(f"No workspace found for {paper_id} under {self.output_root}")
        return sorted(matches, key=lambda path: path.stat().st_mtime, reverse=True)[0]

    def load_metadata(self, paper_id: str) -> dict[str, Any]:
        workspace = self.find_workspace(paper_id)
        metadata = self.load_metadata_from_workspace(workspace)
        if not metadata:
            raise FileNotFoundError(f"metadata.json is missing or invalid for {paper_id}")
        return metadata

    def save_output_file(self, metadata: dict[str, Any], filename: str, content: str) -> Path:
        path = Path(metadata["workspace_path"]) / filename
        write_text_with_backup(path, content)
        files = metadata.setdefault("files", [])
        if filename not in files:
            files.append(filename)
        self.save_metadata(metadata)
        return path

    def list_papers(self) -> list[dict[str, Any]]:
        papers: list[dict[str, Any]] = []
        if not self.output_root.exists():
            return papers
        for metadata_path in self.output_root.glob("* Papers/*/metadata.json"):
            metadata = read_json(metadata_path, {})
            if metadata:
                papers.append(metadata)
        return sorted(papers, key=lambda item: item.get("created_at", ""), reverse=True)

    def rename_workspace(self, metadata: dict[str, Any], new_folder_name: str) -> dict[str, Any]:
        current = Path(metadata["workspace_path"])
        target = ensure_unique_path(current.parent / sanitize_filename_part(new_folder_name, 100))
        if current.resolve() == target.resolve():
            return metadata
        current.rename(target)
        metadata["workspace_path"] = str(target)
        metadata["month_folder"] = str(target.parent)
        self.save_metadata(metadata)
        return metadata
