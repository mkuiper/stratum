"""Analyze paper task implementation."""
from crewai import Task
from pathlib import Path
import yaml
from typing import Dict


def create_analyze_paper_task(
    agent,
    paper_text: str,
    title: str,
    authors: list,
    year: int,
    doi: str,
    config_path: Path = None
) -> Task:
    """
    Create the analyze paper task.

    Args:
        agent: Analyst agent to assign task to
        paper_text: Full text of the paper
        title: Paper title
        authors: List of author names
        year: Publication year
        doi: Paper DOI
        config_path: Optional path to tasks.yaml

    Returns:
        Configured Task
    """
    # Load config
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "tasks.yaml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    task_config = config["analyze_paper"]

    # Format description with inputs
    description = task_config["description"].format(
        paper_text=paper_text[:2000] + "..." if len(paper_text) > 2000 else paper_text,  # Truncate for prompt
        title=title,
        authors=", ".join(authors),
        year=year,
        doi=doi
    )

    expected_output = task_config["expected_output"]

    # Create task
    task = Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )

    return task
