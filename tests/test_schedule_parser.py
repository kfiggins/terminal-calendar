"""Tests for schedule parser module."""

from datetime import date, time
from pathlib import Path

import pytest
from pydantic import ValidationError

from terminal_calendar.models import Schedule, Task
from terminal_calendar.schedule_parser import (
    ScheduleParseError,
    load_schedule,
    load_schedule_dict,
    save_schedule,
    validate_schedule_file,
)

# Get fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestLoadSchedule:
    """Tests for load_schedule function."""

    def test_load_valid_schedule(self) -> None:
        """Test loading a valid schedule file."""
        schedule = load_schedule(FIXTURES_DIR / "valid_schedule.json")

        assert isinstance(schedule, Schedule)
        assert schedule.date == date(2026, 2, 13)
        assert len(schedule.tasks) == 2
        assert schedule.tasks[0].id == "task_1"
        assert schedule.tasks[0].title == "Morning standup"

    def test_load_nonexistent_file(self) -> None:
        """Test loading a file that doesn't exist."""
        with pytest.raises(ScheduleParseError, match="not found"):
            load_schedule(FIXTURES_DIR / "nonexistent.json")

    def test_load_invalid_json(self) -> None:
        """Test loading a file with invalid JSON."""
        with pytest.raises(ScheduleParseError, match="Invalid JSON"):
            load_schedule(FIXTURES_DIR / "invalid_json.json")

    def test_load_invalid_time_range(self) -> None:
        """Test loading a schedule with end time before start time."""
        with pytest.raises(ScheduleParseError, match="validation failed"):
            load_schedule(FIXTURES_DIR / "invalid_time.json")

    def test_load_directory_not_file(self, tmp_path: Path) -> None:
        """Test loading a directory instead of a file."""
        with pytest.raises(ScheduleParseError, match="not a file"):
            load_schedule(tmp_path)


class TestLoadScheduleDict:
    """Tests for load_schedule_dict function."""

    def test_load_valid_dict(self) -> None:
        """Test loading a valid schedule from dictionary."""
        data = {
            "date": "2026-02-13",
            "tasks": [
                {
                    "id": "task_1",
                    "title": "Test task",
                    "start_time": "09:00",
                    "end_time": "10:00",
                    "description": "Testing",
                    "priority": "medium",
                }
            ],
        }

        schedule = load_schedule_dict(data)
        assert schedule.date == date(2026, 2, 13)
        assert len(schedule.tasks) == 1

    def test_load_minimal_task(self) -> None:
        """Test loading a task with only required fields."""
        data = {
            "date": "2026-02-13",
            "tasks": [
                {
                    "id": "task_1",
                    "title": "Minimal",
                    "start_time": "09:00",
                    "end_time": "10:00",
                }
            ],
        }

        schedule = load_schedule_dict(data)
        task = schedule.tasks[0]
        assert task.description == ""
        assert task.priority == "medium"

    def test_load_duplicate_task_ids(self) -> None:
        """Test that duplicate task IDs are rejected."""
        data = {
            "date": "2026-02-13",
            "tasks": [
                {
                    "id": "task_1",
                    "title": "First",
                    "start_time": "09:00",
                    "end_time": "10:00",
                },
                {
                    "id": "task_1",
                    "title": "Duplicate",
                    "start_time": "10:00",
                    "end_time": "11:00",
                },
            ],
        }

        with pytest.raises(ValidationError, match="Duplicate task IDs"):
            load_schedule_dict(data)


class TestValidateScheduleFile:
    """Tests for validate_schedule_file function."""

    def test_validate_valid_file(self) -> None:
        """Test validating a valid schedule file."""
        is_valid, error = validate_schedule_file(FIXTURES_DIR / "valid_schedule.json")
        assert is_valid
        assert error == ""

    def test_validate_invalid_file(self) -> None:
        """Test validating an invalid schedule file."""
        is_valid, error = validate_schedule_file(FIXTURES_DIR / "invalid_json.json")
        assert not is_valid
        assert "Invalid JSON" in error

    def test_validate_nonexistent_file(self) -> None:
        """Test validating a nonexistent file."""
        is_valid, error = validate_schedule_file(FIXTURES_DIR / "nonexistent.json")
        assert not is_valid
        assert "not found" in error


class TestSaveSchedule:
    """Tests for save_schedule function."""

    def test_save_and_load_schedule(self, tmp_path: Path) -> None:
        """Test saving a schedule and loading it back."""
        # Create a schedule
        schedule = Schedule(
            date=date(2026, 2, 13),
            tasks=[
                Task(
                    id="task_1",
                    title="Test task",
                    start_time="09:00",
                    end_time="10:00",
                    description="Testing save",
                    priority="high",
                )
            ],
        )

        # Save it
        save_path = tmp_path / "test_schedule.json"
        save_schedule(schedule, save_path)

        # Load it back
        loaded = load_schedule(save_path)
        assert loaded.date == schedule.date
        assert len(loaded.tasks) == len(schedule.tasks)
        assert loaded.tasks[0].id == schedule.tasks[0].id

    def test_save_creates_directories(self, tmp_path: Path) -> None:
        """Test that save_schedule creates parent directories."""
        schedule = Schedule(
            date=date(2026, 2, 13),
            tasks=[],
        )

        save_path = tmp_path / "subdir" / "nested" / "schedule.json"
        save_schedule(schedule, save_path)

        assert save_path.exists()


class TestTaskSorting:
    """Test that tasks are automatically sorted by start time."""

    def test_tasks_sorted_by_start_time(self) -> None:
        """Test that tasks are sorted by start time when loaded."""
        data = {
            "date": "2026-02-13",
            "tasks": [
                {
                    "id": "task_3",
                    "title": "Late task",
                    "start_time": "15:00",
                    "end_time": "16:00",
                },
                {
                    "id": "task_1",
                    "title": "Early task",
                    "start_time": "09:00",
                    "end_time": "10:00",
                },
                {
                    "id": "task_2",
                    "title": "Mid task",
                    "start_time": "12:00",
                    "end_time": "13:00",
                },
            ],
        }

        schedule = load_schedule_dict(data)
        assert schedule.tasks[0].id == "task_1"
        assert schedule.tasks[1].id == "task_2"
        assert schedule.tasks[2].id == "task_3"


class TestScheduleMethods:
    """Test Schedule model methods."""

    @pytest.fixture
    def sample_schedule(self) -> Schedule:
        """Create a sample schedule for testing."""
        return Schedule(
            date=date(2026, 2, 13),
            tasks=[
                Task(
                    id="task_1",
                    title="Morning",
                    start_time="09:00",
                    end_time="10:00",
                ),
                Task(
                    id="task_2",
                    title="Afternoon",
                    start_time="14:00",
                    end_time="15:00",
                ),
                Task(
                    id="task_3",
                    title="Evening",
                    start_time="17:00",
                    end_time="18:00",
                ),
            ],
        )

    def test_get_task_by_id(self, sample_schedule: Schedule) -> None:
        """Test getting a task by ID."""
        task = sample_schedule.get_task_by_id("task_2")
        assert task is not None
        assert task.title == "Afternoon"

        # Non-existent task
        assert sample_schedule.get_task_by_id("nonexistent") is None

    def test_get_current_task(self, sample_schedule: Schedule) -> None:
        """Test getting the current task at a specific time."""
        # During task 1
        current = sample_schedule.get_current_task(time(9, 30))
        assert current is not None
        assert current.id == "task_1"

        # During task 2
        current = sample_schedule.get_current_task(time(14, 30))
        assert current is not None
        assert current.id == "task_2"

        # Between tasks (no current task)
        current = sample_schedule.get_current_task(time(11, 0))
        assert current is None

    def test_get_upcoming_tasks(self, sample_schedule: Schedule) -> None:
        """Test getting upcoming tasks."""
        # From morning - should get afternoon and evening
        upcoming = sample_schedule.get_upcoming_tasks(time(9, 0), limit=3)
        assert len(upcoming) == 2
        assert upcoming[0].id == "task_2"
        assert upcoming[1].id == "task_3"

        # From afternoon - should get only evening
        upcoming = sample_schedule.get_upcoming_tasks(time(15, 0), limit=3)
        assert len(upcoming) == 1
        assert upcoming[0].id == "task_3"

        # After all tasks
        upcoming = sample_schedule.get_upcoming_tasks(time(20, 0), limit=3)
        assert len(upcoming) == 0


class TestTaskModel:
    """Test Task model methods."""

    def test_get_time_objects(self) -> None:
        """Test converting string times to time objects."""
        task = Task(
            id="test",
            title="Test",
            start_time="09:30",
            end_time="10:45",
        )

        assert task.get_start_time() == time(9, 30)
        assert task.get_end_time() == time(10, 45)

    def test_duration_calculation(self) -> None:
        """Test task duration calculation."""
        task = Task(
            id="test",
            title="Test",
            start_time="09:00",
            end_time="10:30",
        )

        assert task.duration_minutes() == 90
