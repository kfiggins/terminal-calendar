"""Tests for state manager module."""

import datetime as dt
import json
from pathlib import Path

import pytest

from terminal_calendar.models import AppState
from terminal_calendar.state_manager import StateManager, StateManagerError


class TestStateManagerInit:
    """Tests for StateManager initialization."""

    def test_init_with_default_directory(self) -> None:
        """Test initialization with default config directory."""
        manager = StateManager()

        # Should use the default directory
        assert manager.config_dir == Path.home() / ".terminal-calendar"
        assert manager.config_dir.exists()

        # Clean up
        if manager.state_file.exists():
            manager.state_file.unlink()

    def test_init_with_custom_directory(self, tmp_path: Path) -> None:
        """Test initialization with custom config directory."""
        custom_dir = tmp_path / "custom_config"
        manager = StateManager(config_dir=custom_dir)

        assert manager.config_dir == custom_dir
        assert custom_dir.exists()

    def test_state_file_path(self, tmp_path: Path) -> None:
        """Test state file path is set correctly."""
        manager = StateManager(config_dir=tmp_path)
        assert manager.state_file == tmp_path / "state.json"


class TestSaveAndLoadState:
    """Tests for save_state and load_state methods."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> StateManager:
        """Create a state manager with temporary directory."""
        return StateManager(config_dir=tmp_path)

    @pytest.fixture
    def sample_state(self) -> AppState:
        """Create a sample app state."""
        return AppState(
            schedule_file="/path/to/schedule.json",
            schedule_date=dt.date(2026, 2, 13),
            completed_tasks={"task_1", "task_2"},
            last_updated=dt.datetime(2026, 2, 13, 14, 30, 0),
        )

    def test_save_and_load_state(self, manager: StateManager, sample_state: AppState) -> None:
        """Test saving and loading state."""
        # Save state
        manager.save_state(sample_state)
        assert manager.state_file.exists()

        # Load state
        loaded = manager.load_state()
        assert loaded is not None
        assert loaded.schedule_file == sample_state.schedule_file
        assert loaded.schedule_date == sample_state.schedule_date
        assert loaded.completed_tasks == sample_state.completed_tasks

    def test_load_nonexistent_state(self, manager: StateManager) -> None:
        """Test loading state when no state file exists."""
        assert not manager.state_exists()
        loaded = manager.load_state()
        assert loaded is None

    def test_save_creates_parent_dirs(self, tmp_path: Path, sample_state: AppState) -> None:
        """Test that save creates parent directories if needed."""
        nested_dir = tmp_path / "a" / "b" / "c"
        manager = StateManager(config_dir=nested_dir)

        manager.save_state(sample_state)
        assert manager.state_file.exists()

    def test_save_overwrites_existing(self, manager: StateManager, sample_state: AppState) -> None:
        """Test that save overwrites existing state."""
        # Save initial state
        manager.save_state(sample_state)

        # Modify and save again
        sample_state.mark_complete("task_3")
        manager.save_state(sample_state)

        # Load and verify
        loaded = manager.load_state()
        assert loaded is not None
        assert "task_3" in loaded.completed_tasks

    def test_load_invalid_json(self, manager: StateManager) -> None:
        """Test loading state with invalid JSON."""
        # Write invalid JSON
        manager.state_file.write_text("{invalid json}")

        with pytest.raises(StateManagerError, match="Invalid JSON"):
            manager.load_state()

    def test_load_invalid_state_data(self, manager: StateManager) -> None:
        """Test loading state with invalid data structure."""
        # Write valid JSON but invalid state data
        manager.state_file.write_text(json.dumps({"invalid": "data"}))

        with pytest.raises(StateManagerError, match="Invalid state data"):
            manager.load_state()


class TestStateExists:
    """Tests for state_exists method."""

    def test_state_exists_when_file_present(self, tmp_path: Path) -> None:
        """Test state_exists returns True when file exists."""
        manager = StateManager(config_dir=tmp_path)
        manager.state_file.write_text("{}")

        assert manager.state_exists()

    def test_state_exists_when_no_file(self, tmp_path: Path) -> None:
        """Test state_exists returns False when no file."""
        manager = StateManager(config_dir=tmp_path)
        assert not manager.state_exists()


class TestClearState:
    """Tests for clear_state method."""

    def test_clear_existing_state(self, tmp_path: Path) -> None:
        """Test clearing an existing state file."""
        manager = StateManager(config_dir=tmp_path)
        manager.state_file.write_text("{}")

        assert manager.state_exists()
        manager.clear_state()
        assert not manager.state_exists()

    def test_clear_nonexistent_state(self, tmp_path: Path) -> None:
        """Test clearing when no state file exists (should not error)."""
        manager = StateManager(config_dir=tmp_path)
        manager.clear_state()  # Should not raise
        assert not manager.state_exists()


class TestTaskCompletion:
    """Tests for task completion methods."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> StateManager:
        """Create a state manager with saved state."""
        mgr = StateManager(config_dir=tmp_path)
        state = AppState(
            schedule_file="/path/to/schedule.json",
            schedule_date=dt.date(2026, 2, 13),
            completed_tasks={"task_1"},
        )
        mgr.save_state(state)
        return mgr

    def test_mark_task_complete(self, manager: StateManager) -> None:
        """Test marking a task as complete."""
        manager.mark_task_complete("task_2")

        state = manager.load_state()
        assert state is not None
        assert "task_1" in state.completed_tasks
        assert "task_2" in state.completed_tasks

    def test_mark_task_incomplete(self, manager: StateManager) -> None:
        """Test marking a task as incomplete."""
        manager.mark_task_incomplete("task_1")

        state = manager.load_state()
        assert state is not None
        assert "task_1" not in state.completed_tasks

    def test_mark_complete_no_state(self, tmp_path: Path) -> None:
        """Test marking complete when no state exists."""
        manager = StateManager(config_dir=tmp_path)

        with pytest.raises(StateManagerError, match="No state file exists"):
            manager.mark_task_complete("task_1")

    def test_mark_incomplete_no_state(self, tmp_path: Path) -> None:
        """Test marking incomplete when no state exists."""
        manager = StateManager(config_dir=tmp_path)

        with pytest.raises(StateManagerError, match="No state file exists"):
            manager.mark_task_incomplete("task_1")

    def test_get_completed_tasks(self, manager: StateManager) -> None:
        """Test getting completed tasks."""
        completed = manager.get_completed_tasks()
        assert completed == {"task_1"}

    def test_get_completed_tasks_no_state(self, tmp_path: Path) -> None:
        """Test getting completed tasks when no state exists."""
        manager = StateManager(config_dir=tmp_path)
        completed = manager.get_completed_tasks()
        assert completed == set()

    def test_is_task_complete(self, manager: StateManager) -> None:
        """Test checking if a task is complete."""
        assert manager.is_task_complete("task_1")
        assert not manager.is_task_complete("task_2")

    def test_is_task_complete_no_state(self, tmp_path: Path) -> None:
        """Test checking completion when no state exists."""
        manager = StateManager(config_dir=tmp_path)
        assert not manager.is_task_complete("task_1")


class TestReportsDirectory:
    """Tests for reports directory creation."""

    def test_create_reports_dir(self, tmp_path: Path) -> None:
        """Test creating reports directory."""
        manager = StateManager(config_dir=tmp_path)
        reports_dir = manager.create_reports_dir()

        assert reports_dir == tmp_path / "reports"
        assert reports_dir.exists()
        assert reports_dir.is_dir()

    def test_create_reports_dir_idempotent(self, tmp_path: Path) -> None:
        """Test creating reports directory multiple times."""
        manager = StateManager(config_dir=tmp_path)

        # Create twice - should not error
        reports_dir1 = manager.create_reports_dir()
        reports_dir2 = manager.create_reports_dir()

        assert reports_dir1 == reports_dir2
        assert reports_dir1.exists()


class TestGetStateFilePath:
    """Tests for get_state_file_path method."""

    def test_get_state_file_path(self, tmp_path: Path) -> None:
        """Test getting the state file path."""
        manager = StateManager(config_dir=tmp_path)
        path = manager.get_state_file_path()

        assert path == tmp_path / "state.json"
        assert isinstance(path, Path)


class TestIntegration:
    """Integration tests for state manager."""

    def test_full_workflow(self, tmp_path: Path) -> None:
        """Test a complete workflow with state manager."""
        manager = StateManager(config_dir=tmp_path)

        # Initial state - no state file
        assert not manager.state_exists()
        assert manager.load_state() is None

        # Create and save initial state
        state = AppState(
            schedule_file="/schedules/today.json",
            schedule_date=dt.date(2026, 2, 13),
        )
        manager.save_state(state)
        assert manager.state_exists()

        # Mark some tasks complete
        manager.mark_task_complete("task_1")
        manager.mark_task_complete("task_2")

        # Verify completion
        assert manager.is_task_complete("task_1")
        assert manager.is_task_complete("task_2")
        assert not manager.is_task_complete("task_3")

        # Load state and verify
        loaded = manager.load_state()
        assert loaded is not None
        assert loaded.schedule_date == dt.date(2026, 2, 13)
        assert len(loaded.completed_tasks) == 2

        # Mark one incomplete
        manager.mark_task_incomplete("task_1")
        assert not manager.is_task_complete("task_1")
        assert manager.is_task_complete("task_2")

        # Create reports directory
        reports_dir = manager.create_reports_dir()
        assert reports_dir.exists()

        # Clear state
        manager.clear_state()
        assert not manager.state_exists()
