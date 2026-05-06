from __future__ import annotations

from pathlib import Path


class PromptBuilder:
    def __init__(self, prompts_dir: Path) -> None:
        self.prompts_dir = prompts_dir

    def _load(self, filename: str) -> str:
        path = self.prompts_dir / filename
        return path.read_text(encoding="utf-8")

    def build_topic_discovery(
        self, topic_area: str, keywords_or_focus: str, previously_selected_topics: str
    ) -> str:
        template = self._load("01_topic_discovery.txt")
        return (
            template.replace("{TOPIC_AREA}", topic_area)
            .replace("{KEYWORDS_OR_FOCUS}", keywords_or_focus)
            .replace("{PREVIOUSLY_SELECTED_TOPICS}", previously_selected_topics)
        )

    def build_topic_validation(self, selected_topic: str) -> str:
        return self._load("02_topic_validation.txt").replace("{SELECTED_TOPIC}", selected_topic)

    def build_title_abstract(self) -> str:
        return self._load("03_title_abstract.txt")
