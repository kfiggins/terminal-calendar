"""State management for terminal calendar application."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models import AppState


class StateManagerError(Exception):
    """Exception raised when state management fails."""

    pass


class StateManager:
    """Manages application state persistence.

    Handles loading and saving application state to a JSON file,
    including schedule information and task completion status.

    Attributes:
        state_file: Path to the state file
        config_dir: Path to the configuration directory
    """

    DEFAULT_CONFIG_DIR = Path.home() / ".terminal-calendar"
    DEFAULT_STATE_FILE = "state.json"

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize the state manager.

        Args:
            config_dir: Optional custom configuration directory.
                       Defaults to ~/.terminal-calendar
        """
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR
        self.state_file = self.config_dir / self.DEFAULT_STATE_FILE
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StateManagerError(f"Failed to create config directory: {e}") from e

    def save_state(self, state: AppState) -> None:
        """Save application state to disk.

        Args:
            state: The AppState object to save

        Raises:
            StateManagerError: If state cannot be saved
        """
        try:
            # Convert to JSON-serializable dict
            state_dict = state.model_dump(mode="json")

            # Write to file with nice formatting
            with self.state_file.open("w", encoding="utf-8") as f:
                json.dump(state_dict, f, indent=2, ensure_ascii=False)

        except OSError as e:
            raise StateManagerError(f"Failed to save state: {e}") from e
        except Exception as e:
            raise StateManagerError(f"Unexpected error saving state: {e}") from e

    def load_state(self) -> AppState | None:
        """Load application state from disk.

        Returns:
            AppState object if state file exists, None otherwise

        Raises:
            StateManagerError: If state file exists but cannot be loaded
        """
        # If state file doesn't exist, return None (first run)
        if not self.state_file.exists():
            return None

        try:
            with self.state_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate and convert to AppState
            state = AppState.model_validate(data)
            return state

        except json.JSONDecodeError as e:
            raise StateManagerError(f"Invalid JSON in state file: {e}") from e
        except ValidationError as e:
            raise StateManagerError(f"Invalid state data: {e}") from e
        except OSError as e:
            raise StateManagerError(f"Failed to read state file: {e}") from e

    def state_exists(self) -> bool:
        """Check if a state file exists.

        Returns:
            True if state file exists, False otherwise
        """
        return self.state_file.exists()

    def clear_state(self) -> None:
        """Delete the state file.

        Raises:
            StateManagerError: If state file cannot be deleted
        """
        if not self.state_file.exists():
            return

        try:
            self.state_file.unlink()
        except OSError as e:
            raise StateManagerError(f"Failed to delete state file: {e}") from e

    def get_state_file_path(self) -> Path:
        """Get the path to the state file.

        Returns:
            Path to the state file
        """
        return self.state_file

    def mark_task_complete(self, task_id: str) -> None:
        """Mark a task as complete and save state.

        Loads current state, marks task complete, and saves.

        Args:
            task_id: The task ID to mark complete

        Raises:
            StateManagerError: If no state exists or save fails
        """
        state = self.load_state()
        if state is None:
            raise StateManagerError("No state file exists. Load a schedule first.")

        state.mark_complete(task_id)
        self.save_state(state)

    def mark_task_incomplete(self, task_id: str) -> None:
        """Mark a task as incomplete and save state.

        Loads current state, marks task incomplete, and saves.

        Args:
            task_id: The task ID to mark incomplete

        Raises:
            StateManagerError: If no state exists or save fails
        """
        state = self.load_state()
        if state is None:
            raise StateManagerError("No state file exists. Load a schedule first.")

        state.mark_incomplete(task_id)
        self.save_state(state)

    def get_completed_tasks(self) -> set[str]:
        """Get the set of completed task IDs.

        Returns:
            Set of completed task IDs, empty set if no state exists
        """
        state = self.load_state()
        if state is None:
            return set()

        return state.completed_tasks

    def is_task_complete(self, task_id: str) -> bool:
        """Check if a task is marked as complete.

        Args:
            task_id: The task ID to check

        Returns:
            True if complete, False otherwise
        """
        completed = self.get_completed_tasks()
        return task_id in completed

    def create_reports_dir(self) -> Path:
        """Create and return the reports directory.

        Returns:
            Path to the reports directory

        Raises:
            StateManagerError: If directory cannot be created
        """
        reports_dir = self.config_dir / "reports"
        try:
            reports_dir.mkdir(parents=True, exist_ok=True)
            return reports_dir
        except OSError as e:
            raise StateManagerError(f"Failed to create reports directory: {e}") from e
