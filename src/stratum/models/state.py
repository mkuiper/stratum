"""Recursion state management models."""
from pydantic import BaseModel, Field
from typing import Set, Dict


class RecursionState(BaseModel):
    """Tracks processed papers and recursion depth to prevent duplicates."""

    processed_dois: Set[str] = Field(
        default_factory=set,
        description="Set of DOIs that have been processed"
    )
    depth_map: Dict[str, int] = Field(
        default_factory=dict,
        description="Maps DOI to the depth at which it was processed"
    )
    max_depth: int = Field(default=3, ge=0, description="Maximum recursion depth")

    def is_processed(self, doi: str) -> bool:
        """Check if a DOI has already been processed."""
        return doi in self.processed_dois

    def should_process(self, doi: str, current_depth: int) -> bool:
        """
        Determine if a paper should be processed.

        Returns False if:
        - Already processed
        - Current depth >= max_depth
        """
        if self.is_processed(doi):
            return False
        if current_depth >= self.max_depth:
            return False
        return True

    def mark_processed(self, doi: str, depth: int) -> None:
        """Mark a DOI as processed at the given depth."""
        self.processed_dois.add(doi)
        self.depth_map[doi] = depth

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the recursion state."""
        return {
            "total_processed": len(self.processed_dois),
            "max_depth": self.max_depth,
            "papers_by_depth": {
                depth: sum(1 for d in self.depth_map.values() if d == depth)
                for depth in range(self.max_depth)
            }
        }

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "processed_dois": ["10.1000/paper1", "10.1000/paper2"],
                "depth_map": {
                    "10.1000/paper1": 0,
                    "10.1000/paper2": 1
                },
                "max_depth": 3
            }]
        }
    }
