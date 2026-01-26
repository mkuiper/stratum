"""Unit tests for agent creation."""
import pytest
from pathlib import Path

from stratum.agents.librarian import create_librarian_agent
from stratum.agents.analyst import create_analyst_agent, get_analyst_system_prompt
from stratum.agents.archivist import create_archivist_agent


class TestLibrarianAgent:
    """Tests for Librarian agent creation."""

    def test_create_librarian_agent(self):
        """Test Librarian agent creation."""
        agent = create_librarian_agent(llm_model="gpt-4o")

        assert agent is not None
        assert "Librarian" in agent.role
        assert len(agent.tools) == 3  # PaperFetcher, PDFExtractor, CitationFinder
        assert agent.llm is not None  # CrewAI wraps model in LLM object

    def test_librarian_has_correct_tools(self):
        """Test Librarian has the right tools."""
        agent = create_librarian_agent(llm_model="gpt-4o")

        tool_names = [tool.name for tool in agent.tools]
        assert "Paper Fetcher" in tool_names
        assert "PDF Text Extractor" in tool_names
        assert "Citation Finder" in tool_names

    def test_librarian_verbose_setting(self):
        """Test verbose setting from config."""
        agent = create_librarian_agent(llm_model="gpt-4o")
        assert agent.verbose is True  # Default from YAML

    def test_librarian_no_delegation(self):
        """Test delegation is disabled."""
        agent = create_librarian_agent(llm_model="gpt-4o")
        assert agent.allow_delegation is False


class TestAnalystAgent:
    """Tests for Analyst agent creation."""

    def test_create_analyst_agent(self):
        """Test Analyst agent creation."""
        agent = create_analyst_agent(llm_model="gpt-4o")

        assert agent is not None
        assert "Analyst" in agent.role or "Auditor" in agent.role
        assert len(agent.tools) == 0  # Analyst has no tools - pure reasoning
        assert agent.llm is not None  # CrewAI wraps model in LLM object

    def test_analyst_has_no_tools(self):
        """Test Analyst has no tools (reasoning only)."""
        agent = create_analyst_agent(llm_model="gpt-4o")
        assert agent.tools == []

    def test_analyst_backstory_includes_whitesides(self):
        """Test Analyst backstory mentions Whitesides Standard."""
        agent = create_analyst_agent(llm_model="gpt-4o")
        assert "Whitesides" in agent.backstory
        assert "hypothesis" in agent.backstory.lower()
        assert "data" in agent.backstory.lower()

    def test_get_analyst_system_prompt(self):
        """Test getting Analyst system prompt."""
        prompt = get_analyst_system_prompt()

        assert len(prompt) > 0
        assert "Whitesides" in prompt
        assert "hypothesis" in prompt.lower()
        assert "JSON" in prompt


class TestArchivistAgent:
    """Tests for Archivist agent creation."""

    def test_create_archivist_agent(self):
        """Test Archivist agent creation."""
        agent = create_archivist_agent(llm_model="gpt-4o")

        assert agent is not None
        assert "Archivist" in agent.role
        assert len(agent.tools) == 1  # ObsidianFormatterTool
        assert agent.llm is not None  # CrewAI wraps model in LLM object

    def test_archivist_has_obsidian_tool(self):
        """Test Archivist has Obsidian formatter."""
        agent = create_archivist_agent(llm_model="gpt-4o")

        tool_names = [tool.name for tool in agent.tools]
        assert "Obsidian Formatter" in tool_names

    def test_archivist_backstory_mentions_obsidian(self):
        """Test Archivist backstory mentions Obsidian."""
        agent = create_archivist_agent(llm_model="gpt-4o")
        assert "Obsidian" in agent.backstory
        assert "wikilink" in agent.backstory.lower() or "graph" in agent.backstory.lower()


class TestAgentConfiguration:
    """Tests for agent configuration loading."""

    def test_all_agents_use_same_model(self):
        """Test all agents can use the same LLM model."""
        model = "gpt-4o-mini"

        librarian = create_librarian_agent(model)
        analyst = create_analyst_agent(model)
        archivist = create_archivist_agent(model)

        # All agents should have LLM configured
        assert librarian.llm is not None
        assert analyst.llm is not None
        assert archivist.llm is not None

    def test_agents_with_ollama_model(self):
        """Test agents work with Ollama models."""
        model = "ollama/llama3.2"

        librarian = create_librarian_agent(model)
        analyst = create_analyst_agent(model)
        archivist = create_archivist_agent(model)

        # All agents should have LLM configured (CrewAI wraps model string)
        assert librarian.llm is not None
        assert analyst.llm is not None
        assert archivist.llm is not None
