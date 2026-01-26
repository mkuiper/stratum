"""Unit tests for recursion manager."""
import pytest
from pathlib import Path
import json

from stratum.utils.recursion import RecursionManager
from stratum.models.state import RecursionState


class TestRecursionManager:
    """Tests for RecursionManager class."""

    def test_initialization(self, tmp_path):
        """Test RecursionManager initialization."""
        state_file = tmp_path / "state.json"
        manager = RecursionManager(state_file, max_depth=3)

        assert manager.state_file == state_file
        assert manager.max_depth == 3
        assert isinstance(manager.state, RecursionState)

    def test_load_empty_state(self, tmp_path):
        """Test loading state when file doesn't exist."""
        state_file = tmp_path / "nonexistent.json"
        manager = RecursionManager(state_file, max_depth=5)

        assert len(manager.state.processed_dois) == 0
        assert manager.state.max_depth == 5

    def test_save_and_load_state(self, tmp_path):
        """Test saving and loading state."""
        state_file = tmp_path / "state.json"
        manager = RecursionManager(state_file, max_depth=3)

        # Mark some papers as processed
        manager.mark_processed("10.1000/paper1", 0)
        manager.mark_processed("10.1000/paper2", 1)

        # Create new manager with same state file
        manager2 = RecursionManager(state_file, max_depth=3)

        assert len(manager2.state.processed_dois) == 2
        assert "10.1000/paper1" in manager2.state.processed_dois
        assert "10.1000/paper2" in manager2.state.processed_dois

    def test_should_process_paper_new(self, tmp_path):
        """Test should_process_paper for new DOI."""
        state_file = tmp_path / "state.json"
        manager = RecursionManager(state_file, max_depth=3)

        assert manager.should_process_paper("10.1000/new", 0)
        assert manager.should_process_paper("10.1000/new", 2)

    def test_should_not_process_already_processed(self, tmp_path):
        """Test should_process_paper for already processed DOI."""
        state_file = tmp_path / "state.json"
        manager = RecursionManager(state_file, max_depth=3)

        manager.mark_processed("10.1000/paper1", 0)

        assert not manager.should_process_paper("10.1000/paper1", 1)
        assert not manager.should_process_paper("10.1000/paper1", 2)

    def test_should_not_process_at_max_depth(self, tmp_path):
        """Test should_process_paper at max depth."""
        state_file = tmp_path / "state.json"
        manager = RecursionManager(state_file, max_depth=3)

        assert not manager.should_process_paper("10.1000/new", 3)
        assert not manager.should_process_paper("10.1000/new", 4)

    def test_mark_processed_saves_state(self, tmp_path):
        """Test that mark_processed saves to file."""
        state_file = tmp_path / "state.json"
        manager = RecursionManager(state_file, max_depth=3)

        manager.mark_processed("10.1000/paper1", 1)

        # Verify file exists and contains data
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert "10.1000/paper1" in data["processed_dois"]

    def test_get_processed_dois(self, tmp_path):
        """Test getting list of processed DOIs."""
        state_file = tmp_path / "state.json"
        manager = RecursionManager(state_file, max_depth=3)

        manager.mark_processed("10.1000/paper1", 0)
        manager.mark_processed("10.1000/paper2", 1)

        dois = manager.get_processed_dois()
        assert len(dois) == 2
        assert "10.1000/paper1" in dois
        assert "10.1000/paper2" in dois

    def test_get_stats(self, tmp_path):
        """Test getting statistics."""
        state_file = tmp_path / "state.json"
        manager = RecursionManager(state_file, max_depth=3)

        manager.mark_processed("10.1000/paper1", 0)
        manager.mark_processed("10.1000/paper2", 1)
        manager.mark_processed("10.1000/paper3", 1)

        stats = manager.get_stats()
        assert stats["total_processed"] == 3
        assert stats["max_depth"] == 3
        assert stats["papers_by_depth"][0] == 1
        assert stats["papers_by_depth"][1] == 2

    def test_get_papers_at_depth(self, tmp_path):
        """Test getting papers at specific depth."""
        state_file = tmp_path / "state.json"
        manager = RecursionManager(state_file, max_depth=3)

        manager.mark_processed("10.1000/paper1", 0)
        manager.mark_processed("10.1000/paper2", 1)
        manager.mark_processed("10.1000/paper3", 1)
        manager.mark_processed("10.1000/paper4", 2)

        depth_0 = manager.get_papers_at_depth(0)
        depth_1 = manager.get_papers_at_depth(1)
        depth_2 = manager.get_papers_at_depth(2)

        assert len(depth_0) == 1
        assert len(depth_1) == 2
        assert len(depth_2) == 1

    def test_reset(self, tmp_path):
        """Test resetting state."""
        state_file = tmp_path / "state.json"
        manager = RecursionManager(state_file, max_depth=3)

        manager.mark_processed("10.1000/paper1", 0)
        manager.mark_processed("10.1000/paper2", 1)

        manager.reset()

        assert len(manager.state.processed_dois) == 0
        assert len(manager.state.depth_map) == 0

    def test_repr(self, tmp_path):
        """Test string representation."""
        state_file = tmp_path / "state.json"
        manager = RecursionManager(state_file, max_depth=5)

        manager.mark_processed("10.1000/paper1", 0)

        repr_str = repr(manager)
        assert "RecursionManager" in repr_str
        assert "processed=1" in repr_str
        assert "max_depth=5" in repr_str

    def test_corrupted_state_file(self, tmp_path):
        """Test handling of corrupted state file."""
        state_file = tmp_path / "corrupted.json"
        state_file.write_text("this is not valid JSON{[}")

        # Should create empty state despite corrupted file
        manager = RecursionManager(state_file, max_depth=3)
        assert len(manager.state.processed_dois) == 0
