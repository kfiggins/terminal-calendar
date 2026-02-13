"""Integration tests for CLI commands."""

import datetime as dt
import json
from pathlib import Path
import tempfile

import pytest
from click.testing import CliRunner

from terminal_calendar.cli import main
from terminal_calendar.models import Schedule, Task


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_schedule_file(tmp_path: Path) -> Path:
    """Create a temporary schedule file."""
    schedule = Schedule(
        date=dt.date(2024, 3, 15),
        tasks=[
            Task(
                id="task1",
                title="Morning Meeting",
                start_time="09:00",
                end_time="10:00",
                description="Team sync",
                priority="high",
            ),
            Task(
                id="task2",
                title="Code Review",
                start_time="10:00",
                end_time="11:30",
                description="Review PRs",
                priority="medium",
            ),
            Task(
                id="task3",
                title="Lunch",
                start_time="12:00",
                end_time="13:00",
                description="Take a break",
                priority="low",
            ),
        ],
    )

    schedule_file = tmp_path / "schedule.json"
    with schedule_file.open("w", encoding="utf-8") as f:
        json.dump(schedule.model_dump(mode="json"), f, indent=2)

    return schedule_file


@pytest.fixture
def config_dir(tmp_path: Path, monkeypatch) -> Path:
    """Create a temporary config directory and patch StateManager."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Patch the default config directory
    from terminal_calendar import state_manager
    monkeypatch.setattr(
        state_manager.StateManager, "DEFAULT_CONFIG_DIR", config_dir
    )

    return config_dir


class TestLoadCommand:
    """Tests for 'tcal load' command."""

    def test_load_valid_schedule(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test loading a valid schedule file."""
        result = runner.invoke(main, ["load", str(sample_schedule_file)])

        assert result.exit_code == 0
        assert "✓ Schedule loaded successfully!" in result.output
        assert "Date: 2024-03-15" in result.output
        assert "Tasks: 3" in result.output
        assert "Morning Meeting" in result.output

    def test_load_nonexistent_file(
        self, runner: CliRunner, config_dir: Path
    ) -> None:
        """Test loading a nonexistent file."""
        result = runner.invoke(main, ["load", "/nonexistent/file.json"])

        assert result.exit_code != 0
        # Click will error before our code runs due to exists=True

    def test_load_invalid_json(
        self, runner: CliRunner, tmp_path: Path, config_dir: Path
    ) -> None:
        """Test loading an invalid JSON file."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json{")

        result = runner.invoke(main, ["load", str(bad_file)])

        assert result.exit_code != 0
        assert "Error loading schedule" in result.output

    def test_load_creates_state_file(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test that load command creates state file."""
        state_file = config_dir / "state.json"
        assert not state_file.exists()

        result = runner.invoke(main, ["load", str(sample_schedule_file)])

        assert result.exit_code == 0
        assert state_file.exists()

        # Verify state content
        with state_file.open("r") as f:
            state_data = json.load(f)

        assert state_data["schedule_date"] == "2024-03-15"
        assert state_data["completed_tasks"] == []


class TestInfoCommand:
    """Tests for 'tcal info' command."""

    def test_info_with_loaded_schedule(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test info command with a loaded schedule."""
        # First load a schedule
        runner.invoke(main, ["load", str(sample_schedule_file)])

        # Then get info
        result = runner.invoke(main, ["info"])

        assert result.exit_code == 0
        assert "📅 Current Schedule" in result.output
        assert "Date: 2024-03-15" in result.output
        assert "Total tasks: 3" in result.output
        assert "Completed: 0/3 (0%)" in result.output
        assert "Morning Meeting" in result.output

    def test_info_without_loaded_schedule(
        self, runner: CliRunner, config_dir: Path
    ) -> None:
        """Test info command without a loaded schedule."""
        result = runner.invoke(main, ["info"])

        assert result.exit_code != 0
        assert "✗ No schedule loaded" in result.output
        assert "tcal load" in result.output

    def test_info_shows_completion_status(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test that info shows task completion status."""
        # Load and complete a task
        runner.invoke(main, ["load", str(sample_schedule_file)])
        runner.invoke(main, ["complete", "task1"])

        # Get info
        result = runner.invoke(main, ["info"])

        assert result.exit_code == 0
        assert "Completed: 1/3 (33%)" in result.output
        assert "✓" in result.output  # Completed marker


class TestCompleteCommand:
    """Tests for 'tcal complete' command."""

    def test_complete_task(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test marking a task as complete."""
        runner.invoke(main, ["load", str(sample_schedule_file)])

        result = runner.invoke(main, ["complete", "task1"])

        assert result.exit_code == 0
        assert "✓ Task 'Morning Meeting' marked as complete!" in result.output
        assert "Progress: 1/3 tasks (33%)" in result.output

    def test_complete_nonexistent_task(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test completing a nonexistent task."""
        runner.invoke(main, ["load", str(sample_schedule_file)])

        result = runner.invoke(main, ["complete", "nonexistent"])

        assert result.exit_code != 0
        assert "✗ Task 'nonexistent' not found" in result.output
        assert "Available task IDs" in result.output

    def test_complete_without_loaded_schedule(
        self, runner: CliRunner, config_dir: Path
    ) -> None:
        """Test complete command without a loaded schedule."""
        result = runner.invoke(main, ["complete", "task1"])

        assert result.exit_code != 0
        assert "✗ No schedule loaded" in result.output

    def test_complete_undo(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test undoing task completion."""
        runner.invoke(main, ["load", str(sample_schedule_file)])
        runner.invoke(main, ["complete", "task1"])

        # Now undo
        result = runner.invoke(main, ["complete", "--undo", "task1"])

        assert result.exit_code == 0
        assert "✓ Task 'Morning Meeting' marked as incomplete" in result.output
        assert "Progress: 0/3 tasks (0%)" in result.output


class TestStatusCommand:
    """Tests for 'tcal status' command."""

    def test_status_with_loaded_schedule(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test status command with a loaded schedule."""
        runner.invoke(main, ["load", str(sample_schedule_file)])

        result = runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "Friday, March 15, 2024" in result.output
        assert "Current time:" in result.output
        assert "Progress:" in result.output

    def test_status_without_loaded_schedule(
        self, runner: CliRunner, config_dir: Path
    ) -> None:
        """Test status command without a loaded schedule."""
        result = runner.invoke(main, ["status"])

        assert result.exit_code != 0
        assert "✗ No schedule loaded" in result.output


class TestClearCommand:
    """Tests for 'tcal clear' command."""

    def test_clear_with_confirmation(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test clear command with user confirmation."""
        runner.invoke(main, ["load", str(sample_schedule_file)])

        state_file = config_dir / "state.json"
        assert state_file.exists()

        # Confirm the clear
        result = runner.invoke(main, ["clear"], input="y\n")

        assert result.exit_code == 0
        assert "✓ State cleared successfully!" in result.output
        assert not state_file.exists()

    def test_clear_with_cancellation(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test clear command with user cancellation."""
        runner.invoke(main, ["load", str(sample_schedule_file)])

        state_file = config_dir / "state.json"
        assert state_file.exists()

        # Cancel the clear
        result = runner.invoke(main, ["clear"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        assert state_file.exists()  # Should still exist

    def test_clear_without_state(
        self, runner: CliRunner, config_dir: Path
    ) -> None:
        """Test clear command when no state exists."""
        result = runner.invoke(main, ["clear"])

        assert result.exit_code == 0
        assert "No state to clear" in result.output


class TestReportCommand:
    """Tests for 'tcal report' command."""

    def test_report_generates_output(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test that report command generates output."""
        runner.invoke(main, ["load", str(sample_schedule_file)])

        result = runner.invoke(main, ["report"])

        assert result.exit_code == 0
        assert "DAILY PRODUCTIVITY REPORT" in result.output
        assert "SUMMARY" in result.output
        assert "Friday, March 15, 2024" in result.output

    def test_report_saves_to_file(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test that report is saved to file."""
        runner.invoke(main, ["load", str(sample_schedule_file)])

        result = runner.invoke(main, ["report"])

        assert result.exit_code == 0
        assert "✓ Report saved to:" in result.output

        # Check that file exists
        reports_dir = config_dir / "reports"
        report_file = reports_dir / "2024-03-15.txt"
        assert report_file.exists()

    def test_report_no_save(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test report command with --no-save flag."""
        runner.invoke(main, ["load", str(sample_schedule_file)])

        result = runner.invoke(main, ["report", "--no-save"])

        assert result.exit_code == 0
        assert "DAILY PRODUCTIVITY REPORT" in result.output
        assert "✓ Report saved to:" not in result.output

        # File should not exist
        reports_dir = config_dir / "reports"
        if reports_dir.exists():
            report_file = reports_dir / "2024-03-15.txt"
            assert not report_file.exists()

    def test_report_without_loaded_schedule(
        self, runner: CliRunner, config_dir: Path
    ) -> None:
        """Test report command without a loaded schedule."""
        result = runner.invoke(main, ["report"])

        assert result.exit_code != 0
        assert "✗ No schedule loaded" in result.output

    def test_report_with_completed_tasks(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test report with some completed tasks."""
        runner.invoke(main, ["load", str(sample_schedule_file)])
        runner.invoke(main, ["complete", "task1"])
        runner.invoke(main, ["complete", "task2"])

        result = runner.invoke(main, ["report", "--no-save"])

        assert result.exit_code == 0
        assert "Completed:        2" in result.output
        assert "COMPLETED TASKS ✓" in result.output


class TestReportsCommand:
    """Tests for 'tcal reports' command."""

    def test_reports_lists_files(
        self,
        runner: CliRunner,
        sample_schedule_file: Path,
        config_dir: Path,
    ) -> None:
        """Test that reports command lists saved reports."""
        # Generate a report first
        runner.invoke(main, ["load", str(sample_schedule_file)])
        runner.invoke(main, ["report"])

        # List reports
        result = runner.invoke(main, ["reports"])

        assert result.exit_code == 0
        assert "📊 Recent Reports" in result.output
        assert "2024-03-15" in result.output

    def test_reports_empty(
        self, runner: CliRunner, config_dir: Path
    ) -> None:
        """Test reports command with no reports."""
        result = runner.invoke(main, ["reports"])

        assert result.exit_code == 0
        assert "No reports found" in result.output
        assert "tcal report" in result.output


class TestVersion:
    """Tests for version option."""

    def test_version_flag(self, runner: CliRunner) -> None:
        """Test --version flag."""
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "tcal" in result.output
        assert "0.1.0" in result.output


class TestHelp:
    """Tests for help text."""

    def test_help_flag(self, runner: CliRunner) -> None:
        """Test --help flag."""
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Terminal Calendar" in result.output
        assert "Commands:" in result.output

    def test_load_help(self, runner: CliRunner) -> None:
        """Test help for load command."""
        result = runner.invoke(main, ["load", "--help"])

        assert result.exit_code == 0
        assert "Load a schedule file" in result.output

    def test_complete_help(self, runner: CliRunner) -> None:
        """Test help for complete command."""
        result = runner.invoke(main, ["complete", "--help"])

        assert result.exit_code == 0
        assert "Mark a task as complete" in result.output
        assert "--undo" in result.output
