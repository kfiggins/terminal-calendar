"""Schedule parser for loading and validating JSON schedule files."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models import Schedule


class ScheduleParseError(Exception):
    """Exception raised when schedule parsing fails."""

    pass


def load_schedule(file_path: str | Path) -> Schedule:
    """Load and parse a schedule from a JSON file.

    Args:
        file_path: Path to the JSON schedule file

    Returns:
        Validated Schedule object

    Raises:
        ScheduleParseError: If file cannot be read or parsed
        ValidationError: If schedule data is invalid
    """
    path = Path(file_path)

    # Check file exists
    if not path.exists():
        raise ScheduleParseError(f"Schedule file not found: {file_path}")

    # Check file is readable
    if not path.is_file():
        raise ScheduleParseError(f"Path is not a file: {file_path}")

    # Read and parse JSON
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ScheduleParseError(f"Invalid JSON in {file_path}: {e}") from e
    except OSError as e:
        raise ScheduleParseError(f"Error reading file {file_path}: {e}") from e

    # Validate with Pydantic
    try:
        schedule = Schedule.model_validate(data)
    except ValidationError as e:
        # Re-raise with more context
        error_messages = []
        for error in e.errors():
            loc = " -> ".join(str(l) for l in error["loc"])
            msg = error["msg"]
            error_messages.append(f"{loc}: {msg}")

        raise ScheduleParseError(
            f"Schedule validation failed:\n" + "\n".join(f"  - {msg}" for msg in error_messages)
        ) from e

    return schedule


def load_schedule_dict(data: dict[str, Any]) -> Schedule:
    """Load and parse a schedule from a dictionary.

    Useful for testing or when schedule data comes from sources other than files.

    Args:
        data: Dictionary containing schedule data

    Returns:
        Validated Schedule object

    Raises:
        ValidationError: If schedule data is invalid
    """
    return Schedule.model_validate(data)


def validate_schedule_file(file_path: str | Path) -> tuple[bool, str]:
    """Validate a schedule file without raising exceptions.

    Args:
        file_path: Path to the JSON schedule file

    Returns:
        Tuple of (is_valid, error_message)
        If valid: (True, "")
        If invalid: (False, "error message")
    """
    try:
        load_schedule(file_path)
        return (True, "")
    except (ScheduleParseError, ValidationError) as e:
        return (False, str(e))


def save_schedule(schedule: Schedule, file_path: str | Path) -> None:
    """Save a schedule to a JSON file.

    Args:
        schedule: Schedule object to save
        file_path: Path where the schedule should be saved

    Raises:
        ScheduleParseError: If file cannot be written
    """
    path = Path(file_path)

    try:
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON with nice formatting
        with path.open("w", encoding="utf-8") as f:
            json.dump(
                schedule.model_dump(mode="json"),
                f,
                indent=2,
                ensure_ascii=False,
            )
    except OSError as e:
        raise ScheduleParseError(f"Error writing file {file_path}: {e}") from e
