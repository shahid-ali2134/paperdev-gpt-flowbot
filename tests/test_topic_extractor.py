from __future__ import annotations

from core.topic_extractor import extract_first_recommended_topic


def test_extract_first_topic_from_title_line() -> None:
    response = """
1. Open-Set CNN Feature Distance for Rare Medical Lesion Discovery

IEEE-style suggested title: Open-Set CNN Feature Distance for Rare Medical Lesion Discovery

Core idea:
Use calibrated feature distances.
"""
    assert (
        extract_first_recommended_topic(response)
        == "Open-Set CNN Feature Distance for Rare Medical Lesion Discovery"
    )


def test_extract_first_topic_from_markdown_heading() -> None:
    response = """
### 1. Uncertainty-Calibrated Vision Transformers for Low-Prevalence Tumor Boundary Detection

- Core idea: combine uncertainty and boundary attention.
"""
    assert extract_first_recommended_topic(response).startswith(
        "Uncertainty-Calibrated Vision Transformers"
    )


def test_does_not_extract_opening_commentary() -> None:
    response = """
Good--this is exactly the kind of constraint-heavy thinking that leads to strong IEEE papers. Since car detection is saturated, the only way to stand out is to combine it with underexplored dimensions.

1. **Domain-Shift-Aware Nighttime Vehicle Detection Using Synthetic-to-Real Feature Alignment**

Core idea:
Use synthetic adverse-weather scenes.
"""
    assert (
        extract_first_recommended_topic(response)
        == "Domain-Shift-Aware Nighttime Vehicle Detection Using Synthetic-to-Real Feature Alignment"
    )


def test_extracts_marked_first_topic() -> None:
    response = """
FIRST_RECOMMENDED_TOPIC: Open-Set Lesion Discovery Using Calibrated CNN Feature Distance

1. IEEE-style suggested title: Open-Set Lesion Discovery Using Calibrated CNN Feature Distance
"""
    assert (
        extract_first_recommended_topic(response)
        == "Open-Set Lesion Discovery Using Calibrated CNN Feature Distance"
    )
