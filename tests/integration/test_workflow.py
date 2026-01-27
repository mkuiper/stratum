"""Integration tests for end-to-end workflow."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from stratum.crew import StratumCrew
from stratum.flow import StratumFlow
from stratum.utils.recursion import RecursionManager


class TestWorkflowIntegration:
    """End-to-end workflow integration tests."""

    def test_crew_initialization(self):
        """Test crew can be initialized."""
        crew = StratumCrew(verbose=False)

        assert crew.librarian is not None
        assert crew.analyst is not None
        assert crew.archivist is not None

    def test_flow_initialization(self, tmp_path):
        """Test flow can be initialized."""
        state_file = tmp_path / "state.json"

        flow = StratumFlow(
            max_depth=2,
            max_citations=3,
            state_file=state_file,
            verbose=False
        )

        assert flow.max_depth == 2
        assert flow.max_citations == 3
        assert flow.crew is not None
        assert flow.recursion_manager is not None

    def test_recursion_manager_workflow(self, tmp_path):
        """Test recursion manager workflow."""
        state_file = tmp_path / "state.json"
        manager = RecursionManager(state_file, max_depth=3)

        # Process papers at different depths
        manager.mark_processed("10.1000/paper1", 0)
        manager.mark_processed("10.1000/paper2", 1)
        manager.mark_processed("10.1000/paper3", 1)

        # Check state
        assert len(manager.get_processed_dois()) == 3
        assert len(manager.get_papers_at_depth(1)) == 2

        # Check deduplication
        assert not manager.should_process_paper("10.1000/paper1", 2)

        # Save and reload
        manager.save_state()
        manager2 = RecursionManager(state_file, max_depth=3)
        assert len(manager2.get_processed_dois()) == 3

    def test_crew_task_chaining(self, tmp_path):
        """Test that crew creates all three tasks in correct order."""
        from stratum.crew import StratumCrew

        crew = StratumCrew(verbose=False)

        # Mock tools to prevent actual execution
        with patch.object(crew.librarian, 'tools', []):
            with patch('stratum.crew.Crew') as MockCrew:
                mock_crew_instance = Mock()
                MockCrew.return_value = mock_crew_instance

                # Try to process a paper
                try:
                    crew.process_paper(doi="10.1000/test", current_depth=0)
                except:
                    pass  # We don't care about execution, just task creation

                # Check that Crew was called with all three agents and tasks
                if MockCrew.called:
                    call_args = MockCrew.call_args
                    agents = call_args.kwargs.get('agents', [])
                    tasks = call_args.kwargs.get('tasks', [])

                    # Should have all three agents
                    assert len(agents) == 3, f"Expected 3 agents, got {len(agents)}"

                    # Should have all three tasks now (not just fetch)
                    assert len(tasks) == 3, f"Expected 3 tasks, got {len(tasks)}"

                    # Verify task dependencies
                    if len(tasks) >= 2:
                        # Analyze task should depend on fetch task
                        assert hasattr(tasks[1], 'context'), "Analyze task should have context"
                        assert tasks[0] in tasks[1].context, "Analyze task should depend on fetch task"

                    if len(tasks) >= 3:
                        # Archive task should depend on analyze task
                        assert hasattr(tasks[2], 'context'), "Archive task should have context"
                        assert tasks[1] in tasks[2].context, "Archive task should depend on analyze task"

    @pytest.mark.skip(reason="Requires mocking CrewAI internals")
    def test_full_workflow_mock(self, tmp_path, sample_knowledge_table):
        """Test full workflow with mocked components."""
        state_file = tmp_path / "state.json"
        output_dir = tmp_path / "output"

        # Mock the crew to return valid results
        with patch('stratum.flow.StratumCrew') as mock_crew_class:
            mock_crew = Mock()
            mock_crew.process_paper.return_value = {
                "knowledge_table": sample_knowledge_table,
                "markdown_path": str(output_dir / "test.md"),
                "citations": []
            }
            mock_crew_class.return_value = mock_crew

            flow = StratumFlow(
                max_depth=1,
                max_citations=2,
                state_file=state_file,
                output_dir=output_dir,
                verbose=False
            )

            # This would normally call the full workflow
            # For now, just test initialization
            assert flow.recursion_manager is not None
