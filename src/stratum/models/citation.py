"""Citation network models."""
from pydantic import BaseModel, Field
from typing import Literal


class CitationReference(BaseModel):
    """A reference to a cited paper with usage classification."""

    target_paper_doi: str = Field(..., description="DOI of the cited paper")
    target_paper_title: str = Field(..., description="Title of the cited paper")
    usage_type: Literal["Foundational", "Refuting", "Comparison"] = Field(
        ...,
        description="How this citation is used: Foundational (builds on), Refuting (contradicts), Comparison (compares with)"
    )
    notes: str = Field(..., description="Why this citation matters to the current paper")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "target_paper_doi": "10.1000/foundational.2020",
                "target_paper_title": "Original Neural Network Architecture",
                "usage_type": "Foundational",
                "notes": "Provides the baseline architecture that this work extends"
            }]
        }
    }
