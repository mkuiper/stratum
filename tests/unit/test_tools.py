"""Unit tests for Stratum tools."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from stratum.tools.pdf_extractor import PDFTextExtractorTool
from stratum.tools.citation_finder import CitationFinderTool
from stratum.tools.paper_fetcher import PaperFetcherTool
from stratum.tools.obsidian_formatter import ObsidianFormatterTool, kt_to_obsidian


class TestPDFTextExtractorTool:
    """Tests for PDFTextExtractorTool."""

    def test_tool_metadata(self):
        """Test tool has required metadata."""
        tool = PDFTextExtractorTool()
        assert tool.name == "PDF Text Extractor"
        assert len(tool.description) > 0

    def test_nonexistent_file_raises_error(self):
        """Test error raised for non-existent PDF."""
        tool = PDFTextExtractorTool()
        with pytest.raises(FileNotFoundError):
            tool._run("/nonexistent/file.pdf")


class TestCitationFinderTool:
    """Tests for CitationFinderTool."""

    def test_tool_metadata(self):
        """Test tool has required metadata."""
        tool = CitationFinderTool()
        assert tool.name == "Citation Finder"
        assert "GROBID" in tool.description

    def test_nonexistent_file_raises_error(self):
        """Test error raised for non-existent PDF."""
        tool = CitationFinderTool()
        with pytest.raises(FileNotFoundError):
            tool._run("/nonexistent/file.pdf")

    def test_grobid_connection_error(self, tmp_path):
        """Test appropriate error when GROBID is not running."""
        # Create a dummy PDF file
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n")

        tool = CitationFinderTool(grobid_url="http://localhost:9999/api/processReferences")

        with pytest.raises(ConnectionError) as exc:
            tool._run(str(pdf_path))
        assert "GROBID" in str(exc.value)
        assert "docker run" in str(exc.value)

    def test_filter_citations_with_doi(self):
        """Test filtering citations that have DOIs."""
        tool = CitationFinderTool()

        citations = [
            {"title": "Paper 1", "doi": "10.1000/test1"},
            {"title": "Paper 2", "doi": None},
            {"title": "Paper 3", "doi": "10.1000/test3"},
        ]

        filtered = tool.filter_citations_with_doi(citations)
        assert len(filtered) == 2
        assert all(c.get("doi") for c in filtered)

    def test_rank_by_importance(self):
        """Test citation ranking."""
        tool = CitationFinderTool()

        citations = [
            {"title": "Old Paper", "doi": "10.1000/old", "year": 1990, "authors": ["Smith"]},
            {"title": "Recent Paper", "doi": "10.1000/recent", "year": 2023, "authors": ["Doe"]},
            {"title": "No DOI", "doi": None, "year": 2024},
            {"title": "Mid Year", "doi": "10.1000/mid", "year": 2010, "authors": ["Jones"]},
        ]

        ranked = tool.rank_by_importance(citations, max_citations=2)

        assert len(ranked) == 2
        # Recent paper should rank higher
        assert ranked[0]["year"] >= ranked[1]["year"]
        # All ranked papers must have DOI
        assert all(c.get("doi") for c in ranked)


class TestPaperFetcherTool:
    """Tests for PaperFetcherTool."""

    def test_tool_metadata(self):
        """Test tool has required metadata."""
        tool = PaperFetcherTool()
        assert tool.name == "Paper Fetcher"
        assert "DOI" in tool.description or "arXiv" in tool.description

    def test_no_identifier_raises_error(self):
        """Test error raised when no DOI or arXiv ID provided."""
        tool = PaperFetcherTool()
        with pytest.raises(ValueError) as exc:
            tool._run()
        assert "doi" in str(exc.value).lower() or "arxiv" in str(exc.value).lower()

    def test_cache_directory_created(self, tmp_path):
        """Test cache directory is created."""
        cache_dir = tmp_path / "pdf_cache"
        tool = PaperFetcherTool(cache_dir=cache_dir)
        assert cache_dir.exists()

    @patch('stratum.tools.paper_fetcher.requests.get')
    def test_semantic_scholar_fetch(self, mock_get):
        """Test fetching from Semantic Scholar."""
        # Mock Semantic Scholar API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Test Paper",
            "authors": [{"name": "Smith, J."}],
            "year": 2024,
            "abstract": "Test abstract",
            "openAccessPdf": None,
            "externalIds": {}
        }
        mock_get.return_value = mock_response

        tool = PaperFetcherTool()
        result = tool._run(doi="10.1000/test")

        assert result is not None
        assert result["source"] == "semantic_scholar"
        assert result["metadata"]["title"] == "Test Paper"


class TestObsidianFormatterTool:
    """Tests for ObsidianFormatterTool."""

    def test_tool_metadata(self):
        """Test tool has required metadata."""
        tool = ObsidianFormatterTool()
        assert tool.name == "Obsidian Formatter"
        assert "Obsidian" in tool.description

    def test_output_directory_created(self, tmp_path):
        """Test output directory is created."""
        output_dir = tmp_path / "obsidian_output"
        tool = ObsidianFormatterTool(output_dir=output_dir)
        assert output_dir.exists()

    def test_generate_frontmatter(self, sample_knowledge_table):
        """Test YAML frontmatter generation."""
        from stratum.models.knowledge_table import KnowledgeTable

        tool = ObsidianFormatterTool()
        kt = KnowledgeTable(**sample_knowledge_table)
        frontmatter = tool._generate_frontmatter(kt)

        assert frontmatter["kt_id"] == kt.kt_id
        assert frontmatter["title"] == kt.meta.title
        assert frontmatter["year"] == kt.meta.year
        assert frontmatter["doi"] == kt.meta.doi
        assert "knowledge-table" in frontmatter["tags"]

    def test_create_wikilink(self):
        """Test wikilink creation."""
        tool = ObsidianFormatterTool()
        wikilink = tool._create_wikilink("10.1000/test", "Test Paper")

        assert "[[" in wikilink
        assert "]]" in wikilink
        assert "Test Paper" in wikilink

    def test_full_markdown_generation(self, sample_knowledge_table, tmp_path):
        """Test complete markdown generation."""
        tool = ObsidianFormatterTool(output_dir=tmp_path)
        output_path = tool._run(sample_knowledge_table)

        assert Path(output_path).exists()

        # Read and verify content
        content = Path(output_path).read_text()

        # Check frontmatter
        assert "---" in content
        assert "kt_id:" in content

        # Check sections
        assert "# " in content  # Title
        assert "## Central Hypothesis" in content
        assert "## Key Points" in content
        assert "## Logic Chains" in content
        assert "## Citation Network" in content

        # Check KP content
        assert "KP1" in content

        # Check wikilinks
        assert "[[" in content  # Wikilinks present

    def test_kt_to_obsidian_convenience_function(self, sample_knowledge_table, tmp_path):
        """Test convenience function works."""
        # Temporarily set output dir
        with patch('stratum.tools.obsidian_formatter.ObsidianFormatterTool') as mock_tool_class:
            mock_tool = Mock()
            mock_tool._run.return_value = str(tmp_path / "test.md")
            mock_tool_class.return_value = mock_tool

            result = kt_to_obsidian(sample_knowledge_table)
            assert result == str(tmp_path / "test.md")
            mock_tool._run.assert_called_once()

    def test_citation_network_grouping(self, sample_knowledge_table, tmp_path):
        """Test citations are grouped by usage type."""
        # Add multiple citation types
        sample_knowledge_table["citation_network"] = [
            {
                "target_paper_doi": "10.1000/found1",
                "target_paper_title": "Foundational Paper",
                "usage_type": "Foundational",
                "notes": "Base work"
            },
            {
                "target_paper_doi": "10.1000/comp1",
                "target_paper_title": "Comparison Paper",
                "usage_type": "Comparison",
                "notes": "Alternative approach"
            },
            {
                "target_paper_doi": "10.1000/refute1",
                "target_paper_title": "Refuting Paper",
                "usage_type": "Refuting",
                "notes": "Contradicts claim"
            },
        ]

        tool = ObsidianFormatterTool(output_dir=tmp_path)
        output_path = tool._run(sample_knowledge_table)

        content = Path(output_path).read_text()

        # Check all three sections exist
        assert "### Foundational Papers" in content
        assert "### Comparison Papers" in content
        assert "### Refuting Papers" in content

    def test_invalid_kt_json_raises_validation_error(self, tmp_path):
        """Test that invalid KnowledgeTable JSON raises ValidationError."""
        tool = ObsidianFormatterTool(output_dir=tmp_path)

        invalid_kt = {
            "kt_id": "INVALID_FORMAT",  # Wrong format
            "meta": {},
            "core_analysis": {},
        }

        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            tool._run(invalid_kt)
