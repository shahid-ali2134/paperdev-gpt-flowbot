from __future__ import annotations

from typing import Any, TypedDict


class PaperWorkflowState(TypedDict, total=False):
    command: str
    paper_id: str
    paper_number: int
    month_name: str
    year: int
    topic_area: str
    keywords_or_focus: str
    selected_topic: str
    prompt_text: str
    latest_response: str
    output_root: str
    month_folder: str
    workspace_path: str
    metadata: dict[str, Any]
    chat_url: str
    title: str
    abstract: str
    abstract_word_count: int
    chat_name: str
    error: str
    response_file: str
    final_file: str
    rename_error: str
    folder_rename_error: str
