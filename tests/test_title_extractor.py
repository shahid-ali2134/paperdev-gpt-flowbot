from __future__ import annotations

from core.title_extractor import (
    build_clean_final_file,
    count_words,
    extract_abstract,
    extract_title,
    generate_chat_name,
)


def test_extract_title_from_prefixed_line() -> None:
    response = "Refined IEEE conference-style research title: Open-Set CNN Feature Distance for Rail Fault Discovery"
    assert extract_title(response) == "Open-Set CNN Feature Distance for Rail Fault Discovery"


def test_extract_abstract_and_clean_file() -> None:
    response = """
Title: Open-Set CNN Feature Distance for Rail Fault Discovery

Abstract:
This paper proposes a feature-distance open-set learning method for rail fault discovery using public inspection imagery and calibrated uncertainty scoring.

Final novelty points:
1. Distance-aware unknown detection.

Final selected dataset:
Rail surface defect dataset.

Final evaluation metrics:
F1-score, AUROC, open-set detection rate.
"""
    abstract = extract_abstract(response)
    clean, title, extracted_abstract, word_count = build_clean_final_file(response)
    assert title == "Open-Set CNN Feature Distance for Rail Fault Discovery"
    assert abstract == extracted_abstract
    assert count_words(abstract) == word_count
    assert "Paper Title : Open-Set CNN Feature Distance" in clean
    assert "Evaluation Metrics:" not in clean


def test_generate_chat_name_uses_short_meaningful_title() -> None:
    name = generate_chat_name(1, "May", "A Novel Method for Open-Set CNN Feature Distance in Rail Inspection")
    assert name.startswith("P1May ")
    assert "Open Set CNN Feature" in name


def test_extract_abstract_from_numbered_heading() -> None:
    response = """
1. Paper Title:
“Context-Aware Car Detection via Vision-Language Fusion with Scene-Level Semantic Reasoning”

2. IEEE-style Abstract:
This paper introduces a context-aware vehicle detection framework that fuses visual cues with scene-level semantic reasoning to improve robustness under complex traffic conditions. The proposed approach addresses limitations of conventional object detectors that localize vehicles without modeling surrounding road context, occlusion patterns, and semantic scene constraints. By integrating vision-language representations with detection features, the method is expected to distinguish ambiguous vehicle appearances in crowded, low-light, and partially occluded scenes. Experiments can be conducted on public autonomous-driving datasets with adverse-condition subsets to evaluate detection accuracy, robustness, and generalization. The expected contribution is a detection pipeline that moves beyond bounding-box recognition toward semantic, context-guided vehicle understanding for intelligent transportation systems.

Final novelty points:
1. Context reasoning.
"""
    clean, title, abstract, word_count = build_clean_final_file(response)
    assert title == "Context-Aware Car Detection via Vision-Language Fusion with Scene-Level Semantic Reasoning"
    assert abstract.startswith("This paper introduces")
    assert word_count > 50
    assert clean.startswith("Paper Title : Context-Aware")
