"""Fetch paper task implementation."""
from crewai import Task
from pathlib import Path
import yaml
from typing import Dict, Optional, List


def create_fetch_paper_task(
    agent,
    doi: Optional[str] = None,
    pdf_path: Optional[str] = None,
    current_depth: int = 0,
    max_depth: int = 3,
    max_citations: int = 5,
    processed_dois: List[str] = None,
    config_path: Path = None
) -> Task:
    """
    Create the fetch paper task.

    Args:
        agent: Librarian agent to assign task to
        doi: DOI of paper to fetch (if not using local PDF)
        pdf_path: Path to local PDF (if not using DOI)
        current_depth: Current recursion depth
        max_depth: Maximum recursion depth
        max_citations: Maximum citations to extract
        processed_dois: List of already processed DOIs
        config_path: Optional path to tasks.yaml

    Returns:
        Configured Task
    """
    # Load config
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "tasks.yaml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    task_config = config["fetch_paper"]

    # Format description with inputs
    description = task_config["description"].format(
        doi=doi or "N/A",
        pdf_path=pdf_path or "N/A",
        max_citations=max_citations,
        current_depth=current_depth,
        max_depth=max_depth,
        processed_dois=processed_dois or []
    )

    expected_output = task_config["expected_output"].format(
        max_citations=max_citations
    )

    # Create task
    task = Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )

    return task
