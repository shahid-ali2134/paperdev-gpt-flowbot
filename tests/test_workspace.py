from __future__ import annotations

from datetime import datetime

from core.paper_workspace import PaperWorkspaceManager


def test_workspace_creates_monthly_folder_and_metadata(tmp_path) -> None:
    manager = PaperWorkspaceManager(tmp_path)
    metadata = manager.create_workspace(
        topic_area="Machine Vision",
        keywords_or_focus="pattern recognition",
        now=datetime(2026, 5, 6),
    )
    assert metadata["paper_id"] == "P1May"
    assert metadata["paper_number"] == 1
    assert metadata["month_name"] == "May"
    assert "May 2026 Papers" in metadata["month_folder"]
    workspace = tmp_path / "May 2026 Papers" / "P1May Machine Vision Pattern Recognition"
    assert workspace.exists()
    assert (workspace / "metadata.json").exists()


def test_workspace_does_not_overwrite_existing_folder(tmp_path) -> None:
    manager = PaperWorkspaceManager(tmp_path)
    first = manager.create_workspace(
        topic_area="Machine Vision",
        keywords_or_focus="pattern recognition",
        now=datetime(2026, 5, 6),
    )
    second = manager.create_workspace(
        topic_area="Machine Vision",
        keywords_or_focus="pattern recognition",
        now=datetime(2026, 5, 6),
    )
    assert first["paper_id"] == "P1May"
    assert second["paper_id"] == "P2May"
    assert first["workspace_path"] != second["workspace_path"]


def test_rename_workspace_appends_suffix(tmp_path) -> None:
    manager = PaperWorkspaceManager(tmp_path)
    metadata = manager.create_workspace("AI", "fault detection", now=datetime(2026, 5, 6))
    month_folder = tmp_path / "May 2026 Papers"
    (month_folder / "P1May Open Set CNN Feature Distance").mkdir()
    renamed = manager.rename_workspace(metadata, "P1May Open Set CNN Feature Distance")
    assert renamed["workspace_path"].endswith("P1May Open Set CNN Feature Distance - 2")
