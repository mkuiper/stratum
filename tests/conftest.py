"""Pytest fixtures for Stratum tests."""
import pytest
from pathlib import Path


@pytest.fixture
def sample_metadata():
    """Valid paper metadata."""
    return {
        "title": "Machine Learning for Climate Science",
        "authors": ["Smith, J.", "Doe, A.", "Johnson, R."],
        "year": 2024,
        "doi": "10.1000/climate.2024.001"
    }


@pytest.fixture
def sample_citation():
    """Valid citation reference."""
    return {
        "target_paper_doi": "10.1000/foundational.2020",
        "target_paper_title": "Deep Learning Fundamentals",
        "usage_type": "Foundational",
        "notes": "Provides the baseline architecture for our approach"
    }


@pytest.fixture
def sample_key_point():
    """Valid key point."""
    return {
        "id": "KP1",
        "content": "The model achieves 95% accuracy on the test dataset",
        "evidence_anchor": "Table 2",
        "confidence_score": 0.95
    }


@pytest.fixture
def sample_logic_chain():
    """Valid logic chain."""
    return {
        "name": "Performance Argument",
        "argument_flow": "KP1 (baseline) -> KP2 (our results) -> KP3 (significance) -> Conclusion",
        "conclusion_derived": "Our method significantly outperforms the baseline"
    }


@pytest.fixture
def sample_core_analysis():
    """Valid core analysis."""
    return {
        "central_hypothesis": "Deep learning can improve climate prediction accuracy",
        "methodology_summary": "We developed a CNN-LSTM hybrid trained on 50 years of data",
        "significance": "First demonstration of deep learning for multi-decadal climate prediction"
    }


@pytest.fixture
def sample_knowledge_table(sample_metadata, sample_key_point, sample_logic_chain,
                           sample_core_analysis, sample_citation):
    """Complete valid knowledge table."""
    return {
        "kt_id": "KT_2024_Smith",
        "meta": sample_metadata,
        "core_analysis": sample_core_analysis,
        "key_points": [sample_key_point],
        "logic_chains": [sample_logic_chain],
        "citation_network": [sample_citation]
    }


@pytest.fixture
def temp_data_dir(tmp_path):
    """Temporary directory for test data."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "pdfs").mkdir()
    (data_dir / "processed").mkdir()
    (data_dir / "state").mkdir()
    return data_dir
