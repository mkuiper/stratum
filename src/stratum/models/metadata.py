"""Paper metadata models."""
from pydantic import BaseModel, Field
from typing import List


class PaperMetadata(BaseModel):
    """Metadata for a scientific paper."""

    title: str = Field(..., min_length=1, description="Paper title")
    authors: List[str] = Field(..., min_length=1, description="List of author names")
    year: int = Field(..., ge=1900, le=2100, description="Publication year")
    doi: str = Field(..., pattern=r"^10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+$", description="DOI")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "title": "A Novel Approach to Machine Learning",
                "authors": ["Smith, J.", "Doe, A."],
                "year": 2024,
                "doi": "10.1000/example.2024"
            }]
        }
    }
