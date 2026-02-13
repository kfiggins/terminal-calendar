"""Tests for Phase 10 features: config, validation, notes, export, stats."""

import datetime as dt
from pathlib import Path
import tempfile

import pytest

from terminal_calendar.config import ConfigManager, Config
from terminal_calendar.export import export_to_ical, export_to_csv, export_to_json
from terminal_calendar.models import Schedule, Task, AppState
from terminal_calendar.validator import validate_schedule, ValidationWarning


@pytest.fixture
def sample_schedule() -> Schedule:
    """Create a sample schedule."""
    return Schedule(
        date=dt.date(2024, 3, 15),
        tasks=[
            Task(
                id="task1",
                title="Morning Meeting",
                start_time="09:00",
                end_time="10:00",
                priority="high",
            ),
            Task(
                id="task2",
                title="Deep Work",
                start_time="10:00",
                end_time="12:00",
                priority="medium",
            ),
            Task(
                id="task3",
                title="Lunch",
                start_time="12:00",
                end_time="13:00",
                priority="low",
            ),
        ],
    )


@pytest.fixture
def overlapping_schedule() -> Schedule:
    """Create a schedule with overlapping tasks."""
    return Schedule(
        date=dt.date(2024, 3, 15),
        tasks=[
            Task(
                id="task1",
                title="Meeting 1",
                start_time="09:00",
                end_time="10:00",
                priority="high",
            ),
            Task(
                id="task2",
                title="Meeting 2",
                start_time="09:30",
                end_time="10:30",
                priority="high",
            ),
        ],
    )


class TestConfigManager:
    """Tests for configuration management."""

    def test_load_default_config(self) -> None:
        """Test loading default configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_manager = ConfigManager(config_dir=Path(tmpdir))
            config = config_manager.load_config()

            assert isinstance(config, Config)
            assert config.ui.auto_refresh_interval == 60
            assert config.theme.current_task_color == "yellow"
            assert config.validation.warn_overlapping is True

    def test_save_and_load_config(self) -> None:
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_manager = ConfigManager(config_dir=Path(tmpdir))

            # Modify and save
            config = config_manager.load_config()
            config.ui.auto_refresh_interval = 120
            config.theme.current_task_color = "blue"
            config_manager.save_config(config)

            # Load and verify
            loaded_config = config_manager.load_config()
            assert loaded_config.ui.auto_refresh_interval == 120
            assert loaded_config.theme.current_task_color == "blue"

    def test_reset_config(self) -> None:
        """Test resetting configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_manager = ConfigManager(config_dir=Path(tmpdir))

            # Modify
            config = config_manager.load_config()
            config.ui.auto_refresh_interval = 999
            config_manager.save_config(config)

            # Reset
            config_manager.reset_config()
            loaded_config = config_manager.load_config()

            assert loaded_config.ui.auto_refresh_interval == 60  # Default


class TestValidator:
    """Tests for schedule validation."""

    def test_validate_clean_schedule(self, sample_schedule: Schedule) -> None:
        """Test validation of a clean schedule."""
        warnings = validate_schedule(sample_schedule)

        # Should have no errors, maybe warnings about duration
        errors = [w for w in warnings if w.severity == "error"]
        assert len(errors) == 0

    def test_detect_overlapping_tasks(self, overlapping_schedule: Schedule) -> None:
        """Test detection of overlapping tasks."""
        warnings = validate_schedule(overlapping_schedule, warn_overlapping=True)

        # Should have at least one overlap error
        overlap_errors = [w for w in warnings if w.type == "overlap"]
        assert len(overlap_errors) >= 1
        assert "overlap" in overlap_errors[0].message.lower()

    def test_detect_gaps(self, sample_schedule: Schedule) -> None:
        """Test detection of gaps between tasks."""
        # No gaps in sample schedule
        warnings = validate_schedule(
            sample_schedule,
            warn_gaps=True,
            max_gap_minutes=30,
        )

        gap_warnings = [w for w in warnings if w.type in ["short_gap", "large_gap"]]
        assert len(gap_warnings) == 0  # No gaps in this schedule

    def test_detect_short_tasks(self) -> None:
        """Test detection of very short tasks."""
        schedule = Schedule(
            date=dt.date(2024, 3, 15),
            tasks=[
                Task(
                    id="short",
                    title="Very Short",
                    start_time="09:00",
                    end_time="09:02",  # 2 minutes
                    priority="high",
                ),
            ],
        )

        warnings = validate_schedule(schedule)
        short_warnings = [w for w in warnings if w.type == "short_duration"]

        assert len(short_warnings) > 0

    def test_detect_long_tasks(self) -> None:
        """Test detection of very long tasks."""
        schedule = Schedule(
            date=dt.date(2024, 3, 15),
            tasks=[
                Task(
                    id="long",
                    title="Very Long",
                    start_time="09:00",
                    end_time="14:00",  # 5 hours
                    priority="high",
                ),
            ],
        )

        warnings = validate_schedule(schedule)
        long_warnings = [w for w in warnings if w.type == "long_duration"]

        assert len(long_warnings) > 0


class TestTaskNotes:
    """Tests for task notes functionality."""

    def test_add_note_to_task(self) -> None:
        """Test adding a note to a task."""
        state = AppState(
            schedule_file="test.json",
            schedule_date=dt.date(2024, 3, 15),
        )

        state.add_note("task1", "This is a note")

        notes = state.get_notes("task1")
        assert len(notes) == 1
        assert notes[0].content == "This is a note"
        assert isinstance(notes[0].timestamp, dt.datetime)

    def test_add_multiple_notes(self) -> None:
        """Test adding multiple notes to a task."""
        state = AppState(
            schedule_file="test.json",
            schedule_date=dt.date(2024, 3, 15),
        )

        state.add_note("task1", "Note 1")
        state.add_note("task1", "Note 2")
        state.add_note("task1", "Note 3")

        notes = state.get_notes("task1")
        assert len(notes) == 3
        assert notes[0].content == "Note 1"
        assert notes[2].content == "Note 3"

    def test_has_notes(self) -> None:
        """Test checking if a task has notes."""
        state = AppState(
            schedule_file="test.json",
            schedule_date=dt.date(2024, 3, 15),
        )

        assert not state.has_notes("task1")

        state.add_note("task1", "A note")

        assert state.has_notes("task1")
        assert not state.has_notes("task2")

    def test_get_notes_empty(self) -> None:
        """Test getting notes for a task with no notes."""
        state = AppState(
            schedule_file="test.json",
            schedule_date=dt.date(2024, 3, 15),
        )

        notes = state.get_notes("task1")
        assert notes == []


class TestExport:
    """Tests for export functionality."""

    def test_export_to_ical(self, sample_schedule: Schedule) -> None:
        """Test exporting to iCal format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "schedule.ics"
            export_to_ical(sample_schedule, output_path)

            assert output_path.exists()
            content = output_path.read_text()

            assert "BEGIN:VCALENDAR" in content
            assert "END:VCALENDAR" in content
            assert "BEGIN:VEVENT" in content
            assert "Morning Meeting" in content

    def test_export_to_csv(self, sample_schedule: Schedule) -> None:
        """Test exporting to CSV format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "schedule.csv"
            export_to_csv(sample_schedule, output_path)

            assert output_path.exists()
            content = output_path.read_text()

            assert "task_id" in content
            assert "Morning Meeting" in content
            assert "task1" in content

    def test_export_to_csv_with_state(self, sample_schedule: Schedule) -> None:
        """Test exporting to CSV with completion state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AppState(
                schedule_file="test.json",
                schedule_date=sample_schedule.date,
                completed_tasks={"task1"},
            )

            output_path = Path(tmpdir) / "schedule.csv"
            export_to_csv(sample_schedule, output_path, state)

            content = output_path.read_text()
            assert "completed" in content.lower()
            assert "Yes" in content  # task1 is completed

    def test_export_to_json(self, sample_schedule: Schedule) -> None:
        """Test exporting to JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "schedule.json"
            export_to_json(sample_schedule, output_path)

            assert output_path.exists()

            import json
            with output_path.open() as f:
                data = json.load(f)

            assert data["date"] == "2024-03-15"
            assert len(data["tasks"]) == 3
            assert data["tasks"][0]["title"] == "Morning Meeting"

    def test_export_to_json_with_state(self, sample_schedule: Schedule) -> None:
        """Test exporting to JSON with completion state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AppState(
                schedule_file="test.json",
                schedule_date=sample_schedule.date,
                completed_tasks={"task1"},
            )
            state.add_note("task1", "Test note")

            output_path = Path(tmpdir) / "schedule.json"
            export_to_json(sample_schedule, output_path, state, include_notes=True)

            import json
            with output_path.open() as f:
                data = json.load(f)

            # Check completion status
            task1_data = [t for t in data["tasks"] if t["id"] == "task1"][0]
            assert task1_data["completed"] is True

            # Check notes
            assert "notes" in task1_data
            assert len(task1_data["notes"]) == 1
            assert task1_data["notes"][0]["content"] == "Test note"
