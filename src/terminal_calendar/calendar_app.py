"""Textual TUI application for terminal calendar."""

import datetime as dt
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Footer, Header, Static
from textual.reactive import reactive

from .models import Schedule, Task
from .schedule_parser import load_schedule, ScheduleParseError
from .state_manager import StateManager, StateManagerError


class TaskListItem(Static):
    """A single task item in the list."""

    def __init__(
        self,
        task: Task,
        is_current: bool = False,
        is_completed: bool = False,
        **kwargs,
    ) -> None:
        """Initialize task item.

        Args:
            task: The task to display
            is_current: Whether this is the current active task
            is_completed: Whether this task is marked complete
        """
        super().__init__(**kwargs)
        self.task = task
        self.is_current = is_current
        self.is_completed = is_completed

    def render(self) -> str:
        """Render the task item."""
        # Status icon
        if self.is_completed:
            icon = "✓"
            style = "green"
        elif self.is_current:
            icon = "▶"
            style = "yellow bold"
        else:
            icon = "○"
            style = "white"

        # Priority color
        priority_colors = {
            "high": "red",
            "medium": "yellow",
            "low": "green",
        }
        priority_color = priority_colors.get(self.task.priority, "white")

        # Time range
        time_str = f"{self.task.start_time}-{self.task.end_time}"

        # Build the display text
        parts = [
            f"[{style}]{icon}[/]",
            f"[cyan]{time_str}[/]",
            f"[{style}]{self.task.title}[/]",
            f"[{priority_color}][{self.task.priority}][/]",
        ]

        line = " ".join(parts)

        # Add description on second line if present
        if self.task.description:
            desc = self.task.description[:80] + "..." if len(self.task.description) > 80 else self.task.description
            line += f"\n  [dim]{desc}[/]"

        return line


class CalendarView(Static):
    """Main calendar view displaying tasks."""

    current_time: reactive[dt.time] = reactive(dt.datetime.now().time)

    def __init__(
        self,
        schedule: Schedule,
        state_manager: StateManager,
        **kwargs,
    ) -> None:
        """Initialize calendar view.

        Args:
            schedule: The schedule to display
            state_manager: State manager for completion tracking
        """
        super().__init__(**kwargs)
        self.schedule = schedule
        self.state_manager = state_manager

    def compose(self) -> ComposeResult:
        """Compose the calendar view."""
        # Get current state
        state = self.state_manager.load_state()
        completed_tasks = state.completed_tasks if state else set()

        # Get current task
        current_task = self.schedule.get_current_task(self.current_time)

        # Render all tasks
        for task in self.schedule.tasks:
            is_current = current_task is not None and task.id == current_task.id
            is_completed = task.id in completed_tasks

            yield TaskListItem(
                task,
                is_current=is_current,
                is_completed=is_completed,
            )

    def watch_current_time(self, new_time: dt.time) -> None:
        """React to current time changes."""
        # Refresh the task list when time changes
        self.refresh(recompose=True)


class CalendarApp(App):
    """A Textual app for displaying and managing a daily schedule."""

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary;
        color: $text;
    }

    Footer {
        background: $panel;
    }

    #calendar-container {
        height: 100%;
        padding: 1;
    }

    #schedule-info {
        background: $panel;
        color: $text;
        padding: 1;
        margin-bottom: 1;
    }

    #task-list {
        height: 1fr;
        overflow-y: auto;
    }

    TaskListItem {
        padding: 1 2;
        border-bottom: solid $primary-lighten-1;
    }

    .current-task {
        background: $primary-darken-2;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(
        self,
        schedule_file: Path | None = None,
        **kwargs,
    ) -> None:
        """Initialize the calendar app.

        Args:
            schedule_file: Optional path to schedule file (defaults to state)
        """
        super().__init__(**kwargs)
        self.schedule_file = schedule_file
        self.state_manager = StateManager()
        self.schedule: Schedule | None = None

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header(show_clock=True)

        with Container(id="calendar-container"):
            # Schedule info section
            yield Static(self._render_schedule_info(), id="schedule-info")

            # Task list
            with Vertical(id="task-list"):
                if self.schedule:
                    yield CalendarView(self.schedule, self.state_manager)

        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount."""
        # Load schedule
        try:
            self._load_schedule()
        except (ScheduleParseError, StateManagerError) as e:
            self.exit(message=f"Error loading schedule: {e}")
            return

        # Set up auto-refresh timer (every minute)
        self.set_interval(60, self._update_current_time)

        # Update title
        if self.schedule:
            date_str = self.schedule.date.strftime("%A, %B %d, %Y")
            self.title = f"Terminal Calendar - {date_str}"

    def _load_schedule(self) -> None:
        """Load the schedule from file or state."""
        if self.schedule_file:
            # Load from specified file
            self.schedule = load_schedule(self.schedule_file)
        else:
            # Load from state
            state = self.state_manager.load_state()
            if state is None:
                raise StateManagerError(
                    "No schedule loaded. Run 'tcal load <schedule_file>' first."
                )
            self.schedule = load_schedule(state.schedule_file)

    def _render_schedule_info(self) -> str:
        """Render the schedule information header."""
        if not self.schedule:
            return "[yellow]No schedule loaded[/]"

        # Get completion stats
        state = self.state_manager.load_state()
        if state:
            completed = len(state.completed_tasks)
            total = len(self.schedule.tasks)
            pct = state.get_completion_percentage(total)
        else:
            completed = 0
            total = len(self.schedule.tasks)
            pct = 0.0

        # Current time
        now = dt.datetime.now()
        time_str = now.strftime("%H:%M")

        # Current task
        current_task = self.schedule.get_current_task(now.time())
        if current_task:
            current_str = f"▶ {current_task.title}"
        else:
            current_str = "○ No current task"

        # Build info string
        info_lines = [
            f"📅 [bold cyan]{self.schedule.date.strftime('%A, %B %d, %Y')}[/]",
            f"   Current time: [yellow]{time_str}[/]  |  {current_str}",
            f"   Progress: [green]{completed}[/]/{total} tasks ([green]{pct:.0f}%[/] complete)",
        ]

        return "\n".join(info_lines)

    def _update_current_time(self) -> None:
        """Update the current time and refresh display."""
        # Update schedule info
        info_widget = self.query_one("#schedule-info", Static)
        info_widget.update(self._render_schedule_info())

        # Update calendar view
        calendar_view = self.query_one(CalendarView)
        calendar_view.current_time = dt.datetime.now().time()

    def action_refresh(self) -> None:
        """Manually refresh the schedule."""
        try:
            self._load_schedule()
            self._update_current_time()
            self.notify("Schedule refreshed!")
        except (ScheduleParseError, StateManagerError) as e:
            self.notify(f"Error refreshing: {e}", severity="error")

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


def run_calendar_app(schedule_file: Path | None = None) -> None:
    """Run the calendar TUI application.

    Args:
        schedule_file: Optional path to schedule file
    """
    app = CalendarApp(schedule_file=schedule_file)
    app.run()
