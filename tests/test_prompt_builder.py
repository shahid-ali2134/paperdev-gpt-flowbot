from __future__ import annotations

from pathlib import Path

from core.prompt_builder import PromptBuilder


def test_topic_discovery_prompt_replaces_placeholders() -> None:
    builder = PromptBuilder(Path(__file__).resolve().parents[1] / "prompts")
    prompt = builder.build_topic_discovery(
        "Computer Vision",
        "open-set recognition",
        "- P1May: Existing Topic",
    )
    assert "{TOPIC_AREA}" not in prompt
    assert "{KEYWORDS_OR_FOCUS}" not in prompt
    assert "{PREVIOUSLY_SELECTED_TOPICS}" not in prompt
    assert "Computer Vision" in prompt
    assert "open-set recognition" in prompt
    assert "Existing Topic" in prompt


def test_topic_validation_prompt_replaces_selected_topic() -> None:
    builder = PromptBuilder(Path(__file__).resolve().parents[1] / "prompts")
    prompt = builder.build_topic_validation("A rare selected topic")
    assert "{SELECTED_TOPIC}" not in prompt
    assert "A rare selected topic" in prompt
