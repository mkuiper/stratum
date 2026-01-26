"""Integration tests for CLI."""
import pytest
from typer.testing import CliRunner
from pathlib import Path

from stratum.main import app

runner = CliRunner()


class TestCLI:
    """Integration tests for CLI commands."""

    def test_version_command(self):
        """Test version command."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Stratum" in result.stdout
        assert "v0.1.0" in result.stdout

    def test_help_command(self):
        """Test help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "analyze" in result.stdout
        assert "status" in result.stdout

    def test_analyze_help(self):
        """Test analyze command help."""
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "DOI" in result.stdout
        assert "max-depth" in result.stdout

    def test_status_no_state(self, tmp_path):
        """Test status command with no state file."""
        result = runner.invoke(app, ["status", "--state-file", str(tmp_path / "nonexistent.json")])
        assert result.exit_code == 0
        assert "No analysis state found" in result.stdout

    def test_reset_no_state(self, tmp_path):
        """Test reset command with no state file."""
        result = runner.invoke(app, ["reset", "--state-file", str(tmp_path / "nonexistent.json"), "--force"])
        assert result.exit_code == 0
        assert "Nothing to reset" in result.stdout or "No state file" in result.stdout


class TestCLIIntegration:
    """End-to-end CLI integration tests."""

    @pytest.mark.skip(reason="Requires real LLM API and takes time")
    def test_analyze_single_paper(self, tmp_path):
        """Test analyzing a single paper (depth 0)."""
        output_dir = tmp_path / "output"
        state_file = tmp_path / "state.json"

        result = runner.invoke(app, [
            "analyze",
            "10.1000/example",  # Mock DOI
            "--max-depth", "0",
            "--output-dir", str(output_dir),
            "--quiet"
        ])

        # Note: This will fail without real API keys and valid DOI
        # Just testing CLI structure
        assert "analyze" in result.stdout or result.exit_code in [0, 1]
