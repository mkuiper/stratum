"""Analyst agent implementation."""
from crewai import Agent
from pathlib import Path
import yaml


def create_analyst_agent(llm_model: str, config_path: Path = None) -> Agent:
    """
    Create the Analyst agent.

    The Analyst is the core logic engine that extracts Knowledge Tables
    following the Whitesides Standard. It requires no tools - purely
    reasoning-based analysis.

    Args:
        llm_model: LLM model string (e.g., "gpt-4o", "ollama/llama3.2")
        config_path: Optional path to agents.yaml (defaults to config/agents.yaml)

    Returns:
        Configured Analyst Agent
    """
    # Load config
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "agents.yaml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    analyst_config = config["analyst"]

    # No tools needed - Analyst works purely through reasoning and JSON generation
    tools = []

    # Create agent with emphasis on structured output
    agent = Agent(
        role=analyst_config["role"],
        goal=analyst_config["goal"],
        backstory=analyst_config["backstory"],
        tools=tools,
        llm=llm_model,
        verbose=analyst_config.get("verbose", True),
        allow_delegation=analyst_config.get("allow_delegation", False),
    )

    return agent


def get_analyst_system_prompt() -> str:
    """
    Get the system prompt for the Analyst agent.

    This can be used to reinforce the Whitesides Standard rules
    when calling the LLM directly.

    Returns:
        System prompt string
    """
    return """You are a Research Analyst trained in the Whitesides Standard.

CRITICAL RULES:
1. Hypothesis-Driven: Identify what was TESTED, not just what was done
2. Data-Centric: Anchor every Key Point to evidence (Table X, Figure Y)
3. Structure over Time: Organize by logic, not chronology
4. Strict JSON: Output must match KnowledgeTable schema exactly

Your output must be valid JSON that can be parsed by Python's json.loads()
and validated by Pydantic."""
