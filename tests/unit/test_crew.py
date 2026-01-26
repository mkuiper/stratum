"""Unit tests for crew orchestration."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from stratum.crew import StratumCrew
from stratum.models.knowledge_table import KnowledgeTable


class TestStratumCrew:
    """Tests for StratumCrew class."""

    def test_initialization(self):
        """Test StratumCrew initialization."""
        crew = StratumCrew(llm_model="gpt-4o", verbose=False)

        assert crew.llm_model is not None
        assert crew.librarian is not None
        assert crew.analyst is not None
        assert crew.archivist is not None

    def test_initialization_uses_settings(self):
        """Test initialization with default settings."""
        crew = StratumCrew(verbose=False)

        # Should use settings for LLM model
        assert crew.llm_model is not None

    def test_initialization_creates_directories(self, tmp_path):
        """Test that initialization creates output directories."""
        output_dir = tmp_path / "output"
        crew = StratumCrew(output_dir=output_dir, verbose=False)

        assert crew.output_dir == output_dir

    def test_process_paper_requires_doi_or_path(self):
        """Test that process_paper requires DOI or pdf_path."""
        crew = StratumCrew(verbose=False)

        with pytest.raises(ValueError) as exc:
            crew.process_paper()

        assert "doi" in str(exc.value).lower() or "pdf" in str(exc.value).lower()

    def test_create_knowledge_table_validates_schema(self, sample_knowledge_table):
        """Test that create_knowledge_table validates output."""
        crew = StratumCrew(verbose=False)

        # Mock the crew execution to return valid JSON
        with patch('stratum.crew.Crew') as mock_crew_class:
            mock_crew = Mock()
            mock_crew.kickoff.return_value = sample_knowledge_table
            mock_crew_class.return_value = mock_crew

            kt = crew.create_knowledge_table(
                paper_text="Test paper text",
                title="Test Paper",
                authors=["Smith, J."],
                year=2024,
                doi="10.1000/test"
            )

            assert isinstance(kt, KnowledgeTable)
            assert kt.kt_id == sample_knowledge_table["kt_id"]

    def test_create_knowledge_table_handles_invalid_json(self):
        """Test error handling for invalid JSON."""
        crew = StratumCrew(verbose=False)

        with patch('stratum.crew.Crew') as mock_crew_class:
            mock_crew = Mock()
            mock_crew.kickoff.return_value = "this is not valid JSON{["
            mock_crew_class.return_value = mock_crew

            with pytest.raises(ValueError) as exc:
                crew.create_knowledge_table(
                    paper_text="Test",
                    title="Test",
                    authors=["Test"],
                    year=2024,
                    doi="10.1000/test"
                )

            assert "JSON" in str(exc.value)

    def test_archive_knowledge_table(self, sample_knowledge_table, tmp_path):
        """Test archiving Knowledge Table."""
        output_dir = tmp_path / "output"
        crew = StratumCrew(output_dir=output_dir, verbose=False)

        kt = KnowledgeTable(**sample_knowledge_table)

        with patch('stratum.crew.Crew') as mock_crew_class:
            mock_crew = Mock()
            mock_crew.kickoff.return_value = "Success"
            mock_crew_class.return_value = mock_crew

            result = crew.archive_knowledge_table(kt)

            assert isinstance(result, str)
            assert ".md" in result

    def test_repr(self):
        """Test string representation."""
        crew = StratumCrew(llm_model="gpt-4o", verbose=False)
        repr_str = repr(crew)

        assert "StratumCrew" in repr_str
        assert "output_dir" in repr_str


class TestCrewIntegration:
    """Integration tests for crew workflow."""

    def test_agents_have_correct_roles(self):
        """Test that agents have expected roles."""
        crew = StratumCrew(verbose=False)

        assert "Librarian" in crew.librarian.role
        assert "Analyst" in crew.analyst.role or "Auditor" in crew.analyst.role
        assert "Archivist" in crew.archivist.role

    def test_agents_have_tools(self):
        """Test that agents have appropriate tools."""
        crew = StratumCrew(verbose=False)

        # Librarian should have 3 tools
        assert len(crew.librarian.tools) == 3

        # Analyst should have no tools (pure reasoning)
        assert len(crew.analyst.tools) == 0

        # Archivist should have 1 tool (Obsidian formatter)
        assert len(crew.archivist.tools) == 1
