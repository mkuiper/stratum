"""Recursion management utilities."""
from pathlib import Path
from typing import List, Dict
import json

from ..models.state import RecursionState


class RecursionManager:
    """
    Manages recursion depth tracking and paper deduplication.

    Prevents:
    - Reprocessing the same paper multiple times
    - Exceeding maximum recursion depth
    - Losing progress on crashes (state persistence)
    """

    def __init__(self, state_file: Path, max_depth: int = 3):
        """
        Initialize RecursionManager.

        Args:
            state_file: Path to JSON file storing recursion state
            max_depth: Maximum recursion depth
        """
        self.state_file = Path(state_file)
        self.max_depth = max_depth
        self.state = self._load_state()

    def _load_state(self) -> RecursionState:
        """
        Load recursion state from file.

        Returns:
            RecursionState instance (empty if file doesn't exist)
        """
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                return RecursionState(**data)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Warning: Could not load state file: {e}")
                return RecursionState(max_depth=self.max_depth)
        else:
            return RecursionState(max_depth=self.max_depth)

    def save_state(self) -> None:
        """Save current state to file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(self.state.model_dump_json(indent=2))

    def should_process_paper(self, doi: str, current_depth: int) -> bool:
        """
        Determine if a paper should be processed.

        Args:
            doi: DOI of the paper
            current_depth: Current recursion depth

        Returns:
            True if paper should be processed, False otherwise
        """
        return self.state.should_process(doi, current_depth)

    def mark_processed(self, doi: str, depth: int) -> None:
        """
        Mark a paper as processed and save state.

        Args:
            doi: DOI of the paper
            depth: Depth at which it was processed
        """
        self.state.mark_processed(doi, depth)
        self.save_state()

    def get_processed_dois(self) -> List[str]:
        """
        Get list of all processed DOIs.

        Returns:
            List of DOI strings
        """
        return list(self.state.processed_dois)

    def get_stats(self) -> Dict[str, any]:
        """
        Get recursion statistics.

        Returns:
            Dict with statistics
        """
        return self.state.get_stats()

    def get_papers_at_depth(self, depth: int) -> List[str]:
        """
        Get all papers processed at a specific depth.

        Args:
            depth: Recursion depth

        Returns:
            List of DOIs
        """
        return [
            doi for doi, d in self.state.depth_map.items()
            if d == depth
        ]

    def reset(self) -> None:
        """Reset state (clear all processed papers)."""
        self.state = RecursionState(max_depth=self.max_depth)
        self.save_state()

    def __repr__(self) -> str:
        return (
            f"RecursionManager("
            f"processed={len(self.state.processed_dois)}, "
            f"max_depth={self.max_depth})"
        )
