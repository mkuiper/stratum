"""Archive paper task implementation."""
from crewai import Task
from pathlib import Path
import yaml
from typing import Dict
import json


def create_archive_paper_task(
    agent,
    knowledge_table_json: Dict,
    output_dir: str = "./output",
    config_path: Path = None
) -> Task:
    """
    Create the archive paper task.

    Args:
        agent: Archivist agent to assign task to
        knowledge_table_json: Knowledge Table as dict
        output_dir: Directory to save markdown files
        config_path: Optional path to tasks.yaml

    Returns:
        Configured Task
    """
    # Load config
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "tasks.yaml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    task_config = config["archive_paper"]

    # Get kt_id from the JSON
    kt_id = knowledge_table_json.get("kt_id", "unknown")

    # Format description with inputs
    description = task_config["description"].format(
        knowledge_table_json=json.dumps(knowledge_table_json, indent=2),
        output_dir=output_dir,
        kt_id=kt_id
    )

    expected_output = task_config["expected_output"]

    # Create task
    task = Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )

    return task
