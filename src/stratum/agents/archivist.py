"""Archivist agent implementation."""
from crewai import Agent
from pathlib import Path
import yaml

from ..tools.obsidian_formatter import ObsidianFormatterTool


def create_archivist_agent(llm_model: str, config_path: Path = None) -> Agent:
    """
    Create the Archivist agent.

    Args:
        llm_model: LLM model string (e.g., "gpt-4o", "ollama/llama3.2")
        config_path: Optional path to agents.yaml (defaults to config/agents.yaml)

    Returns:
        Configured Archivist Agent
    """
    # Load config
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "agents.yaml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    archivist_config = config["archivist"]

    # Initialize tools
    tools = [
        ObsidianFormatterTool(),
    ]

    # Create agent
    agent = Agent(
        role=archivist_config["role"],
        goal=archivist_config["goal"],
        backstory=archivist_config["backstory"],
        tools=tools,
        llm=llm_model,
        verbose=archivist_config.get("verbose", True),
        allow_delegation=archivist_config.get("allow_delegation", False),
    )

    return agent
