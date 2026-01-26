"""Librarian agent implementation."""
from crewai import Agent
from pathlib import Path
import yaml
from typing import List

from ..tools.pdf_extractor import PDFTextExtractorTool
from ..tools.citation_finder import CitationFinderTool
from ..tools.paper_fetcher import PaperFetcherTool


def create_librarian_agent(llm_model: str, config_path: Path = None) -> Agent:
    """
    Create the Librarian agent.

    Args:
        llm_model: LLM model string (e.g., "gpt-4o", "ollama/llama3.2")
        config_path: Optional path to agents.yaml (defaults to config/agents.yaml)

    Returns:
        Configured Librarian Agent
    """
    # Load config
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "agents.yaml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    librarian_config = config["librarian"]

    # Initialize tools
    tools = [
        PaperFetcherTool(),
        PDFTextExtractorTool(),
        CitationFinderTool(),
    ]

    # Create agent
    agent = Agent(
        role=librarian_config["role"],
        goal=librarian_config["goal"],
        backstory=librarian_config["backstory"],
        tools=tools,
        llm=llm_model,
        verbose=librarian_config.get("verbose", True),
        allow_delegation=librarian_config.get("allow_delegation", False),
    )

    return agent
