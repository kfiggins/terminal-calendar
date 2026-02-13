"""Data models for terminal calendar application."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Task(BaseModel):
    """A single task/event in the schedule.

    Attributes:
        id: Unique identifier for the task
        title: Short title/name of the task
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format
        description: Detailed description of the task
        priority: Task priority level (high, medium, low)
    """

    id: str = Field(..., min_length=1, description="Unique task identifier")
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    start_time: str = Field(..., pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", description="Start time (HH:MM)")
    end_time: str = Field(..., pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", description="End time (HH:MM)")
    description: str = Field(default="", max_length=1000, description="Task description")
    priority: Literal["high", "medium", "low"] = Field(default="medium", description="Task priority")

    @model_validator(mode="after")
    def validate_end_after_start(self) -> "Task":
        """Validate that end_time is after start_time."""
        start_hour, start_min = map(int, self.start_time.split(":"))
        end_hour, end_min = map(int, self.end_time.split(":"))

        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        if end_minutes <= start_minutes:
            raise ValueError(
                f"end_time ({self.end_time}) must be after start_time ({self.start_time})"
            )

        return self

    def get_start_time(self) -> dt.time:
        """Convert start_time string to time object."""
        hour, minute = map(int, self.start_time.split(":"))
        return dt.time(hour=hour, minute=minute)

    def get_end_time(self) -> dt.time:
        """Convert end_time string to time object."""
        hour, minute = map(int, self.end_time.split(":"))
        return dt.time(hour=hour, minute=minute)

    def duration_minutes(self) -> int:
        """Calculate task duration in minutes."""
        start = self.get_start_time()
        end = self.get_end_time()
        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute
        return end_minutes - start_minutes


class Schedule(BaseModel):
    """A daily schedule containing multiple tasks.

    Attributes:
        date: The date for this schedule (YYYY-MM-DD format)
        tasks: List of tasks for the day
    """

    date: dt.date = Field(..., description="Schedule date")
    tasks: list[Task] = Field(default_factory=list, description="List of tasks")

    @field_validator("tasks")
    @classmethod
    def validate_unique_task_ids(cls, v: list[Task]) -> list[Task]:
        """Validate that all task IDs are unique."""
        task_ids = [task.id for task in v]
        if len(task_ids) != len(set(task_ids)):
            duplicates = [tid for tid in task_ids if task_ids.count(tid) > 1]
            raise ValueError(f"Duplicate task IDs found: {set(duplicates)}")
        return v

    @field_validator("tasks")
    @classmethod
    def sort_tasks_by_time(cls, v: list[Task]) -> list[Task]:
        """Sort tasks by start time."""
        return sorted(v, key=lambda t: t.get_start_time())

    def get_task_by_id(self, task_id: str) -> Task | None:
        """Get a task by its ID.

        Args:
            task_id: The task ID to search for

        Returns:
            The Task if found, None otherwise
        """
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_current_task(self, current_time: dt.time | None = None) -> Task | None:
        """Get the task that should be active at the given time.

        Args:
            current_time: The time to check (defaults to now)

        Returns:
            The current Task if found, None otherwise
        """
        if current_time is None:
            current_time = dt.datetime.now().time()

        for task in self.tasks:
            if task.get_start_time() <= current_time < task.get_end_time():
                return task
        return None

    def get_upcoming_tasks(self, current_time: dt.time | None = None, limit: int = 3) -> list[Task]:
        """Get upcoming tasks after the given time.

        Args:
            current_time: The time to check from (defaults to now)
            limit: Maximum number of tasks to return

        Returns:
            List of upcoming tasks
        """
        if current_time is None:
            current_time = dt.datetime.now().time()

        upcoming = [
            task for task in self.tasks
            if task.get_start_time() > current_time
        ]
        return upcoming[:limit]


class TaskNote(BaseModel):
    """A note attached to a task.

    Attributes:
        timestamp: When the note was created
        content: The note content
    """

    timestamp: dt.datetime = Field(default_factory=dt.datetime.now, description="Note timestamp")
    content: str = Field(..., min_length=1, max_length=1000, description="Note content")


class AppState(BaseModel):
    """Application state for persistence.

    Attributes:
        schedule_file: Path to the currently loaded schedule file
        schedule_date: Date of the loaded schedule
        completed_tasks: Set of completed task IDs
        task_notes: Map of task ID to list of notes
        last_updated: Timestamp of last state update
    """

    schedule_file: str = Field(..., min_length=1, description="Path to schedule file")
    schedule_date: dt.date = Field(..., description="Date of the loaded schedule")
    completed_tasks: set[str] = Field(default_factory=set, description="Set of completed task IDs")
    task_notes: dict[str, list[TaskNote]] = Field(default_factory=dict, description="Task notes")
    last_updated: dt.datetime = Field(default_factory=dt.datetime.now, description="Last update timestamp")

    def mark_complete(self, task_id: str) -> None:
        """Mark a task as complete.

        Args:
            task_id: The task ID to mark complete
        """
        self.completed_tasks.add(task_id)
        self.last_updated = dt.datetime.now()

    def mark_incomplete(self, task_id: str) -> None:
        """Mark a task as incomplete.

        Args:
            task_id: The task ID to mark incomplete
        """
        self.completed_tasks.discard(task_id)
        self.last_updated = dt.datetime.now()

    def is_complete(self, task_id: str) -> bool:
        """Check if a task is marked complete.

        Args:
            task_id: The task ID to check

        Returns:
            True if complete, False otherwise
        """
        return task_id in self.completed_tasks

    def get_completion_percentage(self, total_tasks: int) -> float:
        """Calculate completion percentage.

        Args:
            total_tasks: Total number of tasks in schedule

        Returns:
            Completion percentage (0.0 to 100.0)
        """
        if total_tasks == 0:
            return 0.0
        return (len(self.completed_tasks) / total_tasks) * 100.0

    def add_note(self, task_id: str, content: str) -> None:
        """Add a note to a task.

        Args:
            task_id: The task ID to add a note to
            content: The note content
        """
        note = TaskNote(content=content)
        if task_id not in self.task_notes:
            self.task_notes[task_id] = []
        self.task_notes[task_id].append(note)
        self.last_updated = dt.datetime.now()

    def get_notes(self, task_id: str) -> list[TaskNote]:
        """Get all notes for a task.

        Args:
            task_id: The task ID to get notes for

        Returns:
            List of notes (may be empty)
        """
        return self.task_notes.get(task_id, [])

    def has_notes(self, task_id: str) -> bool:
        """Check if a task has any notes.

        Args:
            task_id: The task ID to check

        Returns:
            True if task has notes, False otherwise
        """
        return task_id in self.task_notes and len(self.task_notes[task_id]) > 0
