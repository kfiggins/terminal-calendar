"""Schedule validation for terminal calendar."""

import datetime as dt
from typing import List, Tuple

from .models import Schedule, Task


class ValidationWarning:
    """A validation warning with details.

    Attributes:
        type: Type of warning (overlap, gap, etc.)
        message: Human-readable warning message
        tasks: Tasks involved in the warning
        severity: Severity level (warning, error)
    """

    def __init__(
        self,
        type: str,
        message: str,
        tasks: List[Task] | None = None,
        severity: str = "warning",
    ) -> None:
        """Initialize a validation warning.

        Args:
            type: Type of warning
            message: Warning message
            tasks: Related tasks
            severity: Severity level
        """
        self.type = type
        self.message = message
        self.tasks = tasks or []
        self.severity = severity

    def __str__(self) -> str:
        """String representation of the warning."""
        return f"[{self.severity.upper()}] {self.message}"


def validate_schedule(
    schedule: Schedule,
    warn_overlapping: bool = True,
    warn_gaps: bool = False,
    min_gap_minutes: int = 5,
    max_gap_minutes: int = 120,
) -> List[ValidationWarning]:
    """Validate a schedule for issues.

    Args:
        schedule: The schedule to validate
        warn_overlapping: Check for overlapping tasks
        warn_gaps: Check for large gaps
        min_gap_minutes: Minimum gap for buffer
        max_gap_minutes: Maximum gap before warning

    Returns:
        List of validation warnings
    """
    warnings = []

    if warn_overlapping:
        warnings.extend(_check_overlapping_tasks(schedule))

    if warn_gaps:
        warnings.extend(_check_gaps(schedule, min_gap_minutes, max_gap_minutes))

    warnings.extend(_check_task_duration(schedule))

    return warnings


def _check_overlapping_tasks(schedule: Schedule) -> List[ValidationWarning]:
    """Check for overlapping tasks.

    Args:
        schedule: The schedule to check

    Returns:
        List of warnings for overlapping tasks
    """
    warnings = []
    tasks = schedule.tasks

    for i, task1 in enumerate(tasks):
        for task2 in tasks[i + 1:]:
            if _tasks_overlap(task1, task2):
                message = (
                    f"Tasks overlap: '{task1.title}' ({task1.start_time}-{task1.end_time}) "
                    f"and '{task2.title}' ({task2.start_time}-{task2.end_time})"
                )
                warnings.append(
                    ValidationWarning(
                        type="overlap",
                        message=message,
                        tasks=[task1, task2],
                        severity="error",
                    )
                )

    return warnings


def _tasks_overlap(task1: Task, task2: Task) -> bool:
    """Check if two tasks overlap in time.

    Args:
        task1: First task
        task2: Second task

    Returns:
        True if tasks overlap, False otherwise
    """
    start1 = task1.get_start_time()
    end1 = task1.get_end_time()
    start2 = task2.get_start_time()
    end2 = task2.get_end_time()

    # Convert to minutes for easier comparison
    start1_mins = start1.hour * 60 + start1.minute
    end1_mins = end1.hour * 60 + end1.minute
    start2_mins = start2.hour * 60 + start2.minute
    end2_mins = end2.hour * 60 + end2.minute

    # Check if they overlap
    return not (end1_mins <= start2_mins or end2_mins <= start1_mins)


def _check_gaps(
    schedule: Schedule,
    min_gap_minutes: int,
    max_gap_minutes: int,
) -> List[ValidationWarning]:
    """Check for gaps between tasks.

    Args:
        schedule: The schedule to check
        min_gap_minutes: Minimum gap for transition
        max_gap_minutes: Maximum gap before warning

    Returns:
        List of warnings for gaps
    """
    warnings = []
    tasks = schedule.tasks

    for i in range(len(tasks) - 1):
        task1 = tasks[i]
        task2 = tasks[i + 1]

        gap_minutes = _calculate_gap(task1, task2)

        # Warn about no buffer time
        if 0 < gap_minutes < min_gap_minutes:
            message = (
                f"Short transition time ({gap_minutes}m) between "
                f"'{task1.title}' and '{task2.title}'"
            )
            warnings.append(
                ValidationWarning(
                    type="short_gap",
                    message=message,
                    tasks=[task1, task2],
                    severity="warning",
                )
            )

        # Warn about large gaps
        elif gap_minutes > max_gap_minutes:
            hours = gap_minutes // 60
            mins = gap_minutes % 60
            gap_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

            message = (
                f"Large gap ({gap_str}) between "
                f"'{task1.title}' and '{task2.title}'"
            )
            warnings.append(
                ValidationWarning(
                    type="large_gap",
                    message=message,
                    tasks=[task1, task2],
                    severity="warning",
                )
            )

    return warnings


def _calculate_gap(task1: Task, task2: Task) -> int:
    """Calculate the gap in minutes between two tasks.

    Args:
        task1: First task (earlier)
        task2: Second task (later)

    Returns:
        Gap in minutes
    """
    end1 = task1.get_end_time()
    start2 = task2.get_start_time()

    end1_mins = end1.hour * 60 + end1.minute
    start2_mins = start2.hour * 60 + start2.minute

    return start2_mins - end1_mins


def _check_task_duration(schedule: Schedule) -> List[ValidationWarning]:
    """Check for unrealistic task durations.

    Args:
        schedule: The schedule to check

    Returns:
        List of warnings for duration issues
    """
    warnings = []

    for task in schedule.tasks:
        duration = task.duration_minutes()

        # Warn about very short tasks (< 5 minutes)
        if duration < 5:
            message = (
                f"Very short task ({duration}m): '{task.title}'. "
                "Consider combining with adjacent tasks."
            )
            warnings.append(
                ValidationWarning(
                    type="short_duration",
                    message=message,
                    tasks=[task],
                    severity="warning",
                )
            )

        # Warn about very long tasks (> 4 hours)
        elif duration > 240:
            hours = duration // 60
            message = (
                f"Very long task ({hours}h): '{task.title}'. "
                "Consider breaking into smaller tasks."
            )
            warnings.append(
                ValidationWarning(
                    type="long_duration",
                    message=message,
                    tasks=[task],
                    severity="warning",
                )
            )

    return warnings


def format_validation_report(warnings: List[ValidationWarning]) -> str:
    """Format validation warnings as a readable report.

    Args:
        warnings: List of validation warnings

    Returns:
        Formatted report string
    """
    if not warnings:
        return "✓ No validation issues found"

    lines = ["⚠️  Schedule Validation Warnings:", ""]

    # Group by severity
    errors = [w for w in warnings if w.severity == "error"]
    warnings_list = [w for w in warnings if w.severity == "warning"]

    if errors:
        lines.append("ERRORS:")
        for warning in errors:
            lines.append(f"  ✗ {warning.message}")
        lines.append("")

    if warnings_list:
        lines.append("WARNINGS:")
        for warning in warnings_list:
            lines.append(f"  ⚠ {warning.message}")
        lines.append("")

    lines.append(f"Total: {len(errors)} error(s), {len(warnings_list)} warning(s)")

    return "\n".join(lines)
