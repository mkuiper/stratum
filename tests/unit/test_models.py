"""Unit tests for Pydantic models."""
import pytest
from pydantic import ValidationError

from stratum.models.metadata import PaperMetadata
from stratum.models.citation import CitationReference
from stratum.models.knowledge_table import KeyPoint, LogicChain, KnowledgeTable
from stratum.models.state import RecursionState


class TestPaperMetadata:
    """Tests for PaperMetadata model."""

    def test_valid_metadata(self, sample_metadata):
        """Test creation with valid data."""
        meta = PaperMetadata(**sample_metadata)
        assert meta.title == sample_metadata["title"]
        assert meta.authors == sample_metadata["authors"]
        assert meta.year == sample_metadata["year"]
        assert meta.doi == sample_metadata["doi"]

    def test_invalid_year_too_old(self, sample_metadata):
        """Test validation fails for year < 1900."""
        sample_metadata["year"] = 1899
        with pytest.raises(ValidationError) as exc:
            PaperMetadata(**sample_metadata)
        assert "year" in str(exc.value).lower()

    def test_invalid_year_too_new(self, sample_metadata):
        """Test validation fails for year > 2100."""
        sample_metadata["year"] = 2101
        with pytest.raises(ValidationError) as exc:
            PaperMetadata(**sample_metadata)
        assert "year" in str(exc.value).lower()

    def test_invalid_doi_format(self, sample_metadata):
        """Test validation fails for invalid DOI."""
        sample_metadata["doi"] = "not-a-doi"
        with pytest.raises(ValidationError) as exc:
            PaperMetadata(**sample_metadata)
        assert "doi" in str(exc.value).lower()

    def test_empty_authors(self, sample_metadata):
        """Test validation fails for empty authors list."""
        sample_metadata["authors"] = []
        with pytest.raises(ValidationError) as exc:
            PaperMetadata(**sample_metadata)
        assert "authors" in str(exc.value).lower()


class TestCitationReference:
    """Tests for CitationReference model."""

    def test_valid_citation(self, sample_citation):
        """Test creation with valid data."""
        cite = CitationReference(**sample_citation)
        assert cite.target_paper_doi == sample_citation["target_paper_doi"]
        assert cite.usage_type == sample_citation["usage_type"]

    def test_valid_usage_types(self, sample_citation):
        """Test all valid usage types."""
        for usage_type in ["Foundational", "Refuting", "Comparison"]:
            sample_citation["usage_type"] = usage_type
            cite = CitationReference(**sample_citation)
            assert cite.usage_type == usage_type

    def test_invalid_usage_type(self, sample_citation):
        """Test validation fails for invalid usage type."""
        sample_citation["usage_type"] = "InvalidType"
        with pytest.raises(ValidationError) as exc:
            CitationReference(**sample_citation)
        assert "usage_type" in str(exc.value).lower()


class TestKeyPoint:
    """Tests for KeyPoint model."""

    def test_valid_key_point(self, sample_key_point):
        """Test creation with valid data."""
        kp = KeyPoint(**sample_key_point)
        assert kp.id == sample_key_point["id"]
        assert kp.content == sample_key_point["content"]
        assert kp.confidence_score == sample_key_point["confidence_score"]

    def test_invalid_id_format(self, sample_key_point):
        """Test validation fails for invalid ID format."""
        sample_key_point["id"] = "INVALID"
        with pytest.raises(ValidationError) as exc:
            KeyPoint(**sample_key_point)
        assert "id" in str(exc.value).lower()

    def test_valid_id_formats(self, sample_key_point):
        """Test various valid ID formats."""
        for valid_id in ["KP1", "KP10", "KP999"]:
            sample_key_point["id"] = valid_id
            kp = KeyPoint(**sample_key_point)
            assert kp.id == valid_id

    def test_content_too_short(self, sample_key_point):
        """Test validation fails for content < 10 chars."""
        sample_key_point["content"] = "Short"
        with pytest.raises(ValidationError) as exc:
            KeyPoint(**sample_key_point)
        assert "content" in str(exc.value).lower()

    def test_confidence_score_range(self, sample_key_point):
        """Test confidence score must be 0.0-1.0."""
        # Test too low
        sample_key_point["confidence_score"] = -0.1
        with pytest.raises(ValidationError):
            KeyPoint(**sample_key_point)

        # Test too high
        sample_key_point["confidence_score"] = 1.1
        with pytest.raises(ValidationError):
            KeyPoint(**sample_key_point)

        # Test valid boundaries
        for score in [0.0, 0.5, 1.0]:
            sample_key_point["confidence_score"] = score
            kp = KeyPoint(**sample_key_point)
            assert kp.confidence_score == score


class TestLogicChain:
    """Tests for LogicChain model."""

    def test_valid_logic_chain(self, sample_logic_chain):
        """Test creation with valid data."""
        lc = LogicChain(**sample_logic_chain)
        assert lc.name == sample_logic_chain["name"]
        assert lc.argument_flow == sample_logic_chain["argument_flow"]
        assert lc.conclusion_derived == sample_logic_chain["conclusion_derived"]


class TestKnowledgeTable:
    """Tests for KnowledgeTable model."""

    def test_valid_knowledge_table(self, sample_knowledge_table):
        """Test creation with valid complete data."""
        kt = KnowledgeTable(**sample_knowledge_table)
        assert kt.kt_id == sample_knowledge_table["kt_id"]
        assert kt.meta.title == sample_knowledge_table["meta"]["title"]
        assert len(kt.key_points) == 1
        assert len(kt.logic_chains) == 1
        assert len(kt.citation_network) == 1

    def test_invalid_kt_id_format(self, sample_knowledge_table):
        """Test validation fails for invalid KT_ID format."""
        invalid_ids = ["INVALID", "KT_2024", "2024_Smith", "KT_Smith_2024"]
        for invalid_id in invalid_ids:
            sample_knowledge_table["kt_id"] = invalid_id
            with pytest.raises(ValidationError) as exc:
                KnowledgeTable(**sample_knowledge_table)
            assert "kt_id" in str(exc.value).lower()

    def test_valid_kt_id_formats(self, sample_knowledge_table):
        """Test various valid KT_ID formats."""
        valid_ids = ["KT_2024_Smith", "KT_2020_Doe", "KT_1999_Johnson"]
        for valid_id in valid_ids:
            sample_knowledge_table["kt_id"] = valid_id
            kt = KnowledgeTable(**sample_knowledge_table)
            assert kt.kt_id == valid_id

    def test_kt_id_year_validation(self, sample_knowledge_table):
        """Test year in KT_ID must be valid."""
        sample_knowledge_table["kt_id"] = "KT_1800_Smith"
        with pytest.raises(ValidationError) as exc:
            KnowledgeTable(**sample_knowledge_table)
        assert "year" in str(exc.value).lower()

    def test_missing_core_analysis_field(self, sample_knowledge_table):
        """Test validation fails if core_analysis missing required fields."""
        del sample_knowledge_table["core_analysis"]["central_hypothesis"]
        with pytest.raises(ValidationError) as exc:
            KnowledgeTable(**sample_knowledge_table)
        assert "central_hypothesis" in str(exc.value).lower()

    def test_empty_core_analysis_field(self, sample_knowledge_table):
        """Test validation fails if core_analysis field is empty."""
        sample_knowledge_table["core_analysis"]["central_hypothesis"] = ""
        with pytest.raises(ValidationError) as exc:
            KnowledgeTable(**sample_knowledge_table)
        assert "non-empty" in str(exc.value).lower()

    def test_all_core_analysis_fields_required(self, sample_knowledge_table):
        """Test all three core_analysis fields are required."""
        required_fields = ["central_hypothesis", "methodology_summary", "significance"]
        for field in required_fields:
            kt_copy = sample_knowledge_table.copy()
            kt_copy["core_analysis"] = sample_knowledge_table["core_analysis"].copy()
            del kt_copy["core_analysis"][field]
            with pytest.raises(ValidationError) as exc:
                KnowledgeTable(**kt_copy)
            assert field in str(exc.value).lower()

    def test_empty_key_points_fails(self, sample_knowledge_table):
        """Test validation fails if key_points is empty."""
        sample_knowledge_table["key_points"] = []
        with pytest.raises(ValidationError) as exc:
            KnowledgeTable(**sample_knowledge_table)

    def test_empty_logic_chains_fails(self, sample_knowledge_table):
        """Test validation fails if logic_chains is empty."""
        sample_knowledge_table["logic_chains"] = []
        with pytest.raises(ValidationError) as exc:
            KnowledgeTable(**sample_knowledge_table)

    def test_empty_citation_network_allowed(self, sample_knowledge_table):
        """Test citation_network can be empty (papers may have no citations)."""
        sample_knowledge_table["citation_network"] = []
        kt = KnowledgeTable(**sample_knowledge_table)
        assert len(kt.citation_network) == 0

    def test_json_serialization(self, sample_knowledge_table):
        """Test model can be serialized to JSON."""
        kt = KnowledgeTable(**sample_knowledge_table)
        json_str = kt.model_dump_json()
        assert isinstance(json_str, str)
        assert "KT_2024_Smith" in json_str

    def test_json_deserialization(self, sample_knowledge_table):
        """Test model can be created from JSON."""
        kt = KnowledgeTable(**sample_knowledge_table)
        json_str = kt.model_dump_json()
        kt_reloaded = KnowledgeTable.model_validate_json(json_str)
        assert kt_reloaded.kt_id == kt.kt_id
        assert kt_reloaded.meta.title == kt.meta.title


class TestRecursionState:
    """Tests for RecursionState model."""

    def test_empty_state(self):
        """Test creation of empty state."""
        state = RecursionState()
        assert len(state.processed_dois) == 0
        assert len(state.depth_map) == 0
        assert state.max_depth == 3

    def test_custom_max_depth(self):
        """Test setting custom max depth."""
        state = RecursionState(max_depth=5)
        assert state.max_depth == 5

    def test_is_processed(self):
        """Test checking if DOI is processed."""
        state = RecursionState()
        doi = "10.1000/test"

        assert not state.is_processed(doi)
        state.mark_processed(doi, 0)
        assert state.is_processed(doi)

    def test_should_process_new_doi(self):
        """Test should process new DOI at valid depth."""
        state = RecursionState(max_depth=3)
        assert state.should_process("10.1000/new", 0)
        assert state.should_process("10.1000/new", 2)

    def test_should_not_process_at_max_depth(self):
        """Test should not process at max depth."""
        state = RecursionState(max_depth=3)
        assert not state.should_process("10.1000/new", 3)
        assert not state.should_process("10.1000/new", 4)

    def test_should_not_process_already_processed(self):
        """Test should not process already processed DOI."""
        state = RecursionState(max_depth=3)
        doi = "10.1000/test"

        state.mark_processed(doi, 0)
        assert not state.should_process(doi, 1)
        assert not state.should_process(doi, 2)

    def test_mark_processed(self):
        """Test marking DOI as processed."""
        state = RecursionState()
        doi = "10.1000/test"

        state.mark_processed(doi, 1)
        assert doi in state.processed_dois
        assert state.depth_map[doi] == 1

    def test_get_stats(self):
        """Test getting recursion statistics."""
        state = RecursionState(max_depth=3)

        state.mark_processed("10.1000/paper1", 0)
        state.mark_processed("10.1000/paper2", 1)
        state.mark_processed("10.1000/paper3", 1)

        stats = state.get_stats()
        assert stats["total_processed"] == 3
        assert stats["max_depth"] == 3
        assert stats["papers_by_depth"][0] == 1
        assert stats["papers_by_depth"][1] == 2

    def test_state_persistence(self):
        """Test state can be serialized and deserialized."""
        state = RecursionState(max_depth=5)
        state.mark_processed("10.1000/paper1", 0)
        state.mark_processed("10.1000/paper2", 1)

        # Serialize
        json_str = state.model_dump_json()

        # Deserialize
        state_reloaded = RecursionState.model_validate_json(json_str)
        assert state_reloaded.max_depth == 5
        assert len(state_reloaded.processed_dois) == 2
        assert state_reloaded.is_processed("10.1000/paper1")
        assert state_reloaded.depth_map["10.1000/paper2"] == 1
