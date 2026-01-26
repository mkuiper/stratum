"""Core Knowledge Table schema - the data contract for all agents."""
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any
from .metadata import PaperMetadata
from .citation import CitationReference


class KeyPoint(BaseModel):
    """An atomic fact or claim from the paper with evidence."""

    id: str = Field(..., pattern=r"^KP\d+$", description="Unique identifier (e.g., KP1, KP2)")
    content: str = Field(..., min_length=10, description="The specific claim or finding")
    evidence_anchor: str = Field(
        ...,
        description="Reference to supporting evidence (e.g., 'Table 1', 'Figure 3', 'Equation 2')"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this claim based on evidence strength"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "KP1",
                "content": "The proposed model achieves 95% accuracy on the test set",
                "evidence_anchor": "Table 2",
                "confidence_score": 0.95
            }]
        }
    }


class LogicChain(BaseModel):
    """A logical argument connecting hypothesis to conclusion."""

    name: str = Field(..., description="Name of this argument thread")
    argument_flow: str = Field(
        ...,
        description="Step-by-step logical progression (e.g., 'KP1 establishes X -> KP3 shows Y -> Therefore Z')"
    )
    conclusion_derived: str = Field(..., description="The conclusion reached by this logic chain")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "name": "Performance Superiority Argument",
                "argument_flow": "KP1 (baseline accuracy) -> KP2 (our model accuracy) -> KP3 (statistical significance) -> Our model significantly outperforms baseline",
                "conclusion_derived": "The proposed architecture demonstrates statistically significant improvement over existing methods"
            }]
        }
    }


class KnowledgeTable(BaseModel):
    """
    Complete knowledge table for a scientific paper.

    Follows the Whitesides Standard: papers are organized descriptions
    of hypotheses, data, and conclusions.
    """

    kt_id: str = Field(
        ...,
        pattern=r"^KT_\d{4}_\w{3,}$",
        description="Unique Knowledge Table ID (format: KT_YYYY_XXX)"
    )
    meta: PaperMetadata
    core_analysis: Dict[str, Any] = Field(
        ...,
        description="Must contain: central_hypothesis, methodology_summary, significance"
    )
    key_points: List[KeyPoint] = Field(..., min_length=1, description="Atomic claims with evidence")
    logic_chains: List[LogicChain] = Field(..., min_length=1, description="Argument threads")
    citation_network: List[CitationReference] = Field(
        default_factory=list,
        description="Citations with usage classification"
    )

    @field_validator('core_analysis')
    @classmethod
    def validate_core_analysis(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure core_analysis contains required fields."""
        required = {'central_hypothesis', 'methodology_summary', 'significance'}
        missing = required - set(v.keys())
        if missing:
            raise ValueError(f"Missing required core_analysis fields: {missing}")

        # Validate non-empty strings
        for field in required:
            if not isinstance(v[field], str) or len(v[field].strip()) == 0:
                raise ValueError(f"core_analysis.{field} must be a non-empty string")

        return v

    @field_validator('kt_id')
    @classmethod
    def validate_kt_id_format(cls, v: str) -> str:
        """Validate KT_ID format and extract year."""
        parts = v.split('_')
        if len(parts) != 3:
            raise ValueError("kt_id must have format KT_YYYY_XXX")

        year = int(parts[1])
        if year < 1900 or year > 2100:
            raise ValueError(f"Year in kt_id must be between 1900 and 2100, got {year}")

        return v

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "kt_id": "KT_2024_Smith",
                "meta": {
                    "title": "Deep Learning for Climate Prediction",
                    "authors": ["Smith, J.", "Doe, A."],
                    "year": 2024,
                    "doi": "10.1000/climate.2024"
                },
                "core_analysis": {
                    "central_hypothesis": "Deep neural networks can improve long-term climate prediction accuracy compared to traditional models",
                    "methodology_summary": "Developed a hybrid CNN-LSTM architecture trained on 50 years of climate data, compared against ARIMA baseline",
                    "significance": "First demonstration that deep learning can capture non-linear climate dynamics at multi-decadal timescales"
                },
                "key_points": [
                    {
                        "id": "KP1",
                        "content": "Proposed model achieves 23% lower RMSE than baseline",
                        "evidence_anchor": "Table 3",
                        "confidence_score": 0.92
                    }
                ],
                "logic_chains": [
                    {
                        "name": "Performance Improvement",
                        "argument_flow": "KP1 shows lower error -> KP2 shows statistical significance -> Conclusion: model is superior",
                        "conclusion_derived": "The deep learning approach significantly outperforms traditional methods"
                    }
                ],
                "citation_network": [
                    {
                        "target_paper_doi": "10.1000/lstm.2015",
                        "target_paper_title": "LSTM Networks for Sequence Prediction",
                        "usage_type": "Foundational",
                        "notes": "Provides the core LSTM architecture used in our model"
                    }
                ]
            }]
        }
    }
