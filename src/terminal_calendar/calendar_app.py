"""Textual TUI application for terminal calendar."""

import datetime as dt
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static, ListItem, ListView, ProgressBar
from textual.reactive import reactive

from .models import Schedule, Task
from .schedule_parser import load_schedule, ScheduleParseError
from .state_manager import StateManager, StateManagerError


class TaskListItem(ListItem):
    """A selectable task item in the list."""

    def __init__(
        self,
        task: Task,
        is_current: bool = False,
        is_completed: bool = False,
        is_past: bool = False,
        **kwargs,
    ) -> None:
        """Initialize task item.

        Args:
            task: The task to display
            is_current: Whether this is the current active task
            is_completed: Whether this task is marked complete
            is_past: Whether this task is in the past
        """
        super().__init__(**kwargs)
        self.task = task
        self.is_current = is_current
        self.is_completed = is_completed
        self.is_past = is_past

    def render(self) -> str:
        """Render the task item."""
        # Base styling
        base_style = "dim" if self.is_past and not self.is_completed else ""

        # Status icon and style
        if self.is_completed:
            icon = "✓"
            icon_style = "bold green"
            title_style = "green"
        elif self.is_current:
            icon = "▶"
            icon_style = "bold yellow"
            title_style = "bold yellow"
        else:
            icon = "○"
            icon_style = "white"
            title_style = "white"

        # Apply dimming to past tasks
        if base_style:
            icon_style = f"{icon_style} {base_style}"
            title_style = f"{title_style} {base_style}"

        # Priority indicator with color
        priority_colors = {
            "high": "red",
            "medium": "yellow",
            "low": "green",
        }
        priority_color = priority_colors.get(self.task.priority, "white")
        if base_style:
            priority_color = f"{priority_color} {base_style}"

        # Priority badge
        priority_badges = {
            "high": "!!!",
            "medium": "!!",
            "low": "!",
        }
        priority_badge = priority_badges.get(self.task.priority, "")

        # Time range
        time_str = f"{self.task.start_time}-{self.task.end_time}"
        time_style = f"bold cyan" if not base_style else f"cyan {base_style}"

        # Build the display text with better spacing
        parts = [
            f"[{icon_style}]{icon:2}[/]",
            f"[{time_style}]{time_str}[/]",
            f"[{title_style}]{self.task.title}[/]",
            f"[{priority_color}]{priority_badge}[/]",
        ]

        line = "  ".join(parts)

        # Add description on second line if present
        if self.task.description:
            desc = self.task.description[:75] + "..." if len(self.task.description) > 75 else self.task.description
            desc_style = f"dim italic" if not base_style else "dim"
            line += f"\n     [{desc_style}]{desc}[/]"

        # Add duration hint
        duration = self.task.duration_minutes()
        hours = duration // 60
        mins = duration % 60
        if hours > 0:
            duration_str = f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
        else:
            duration_str = f"{mins}m"
        line += f"\n     [{base_style if base_style else 'dim'}]Duration: {duration_str}[/]"

        return line


class DayProgressBar(Static):
    """A custom progress bar showing day completion."""

    def __init__(self, completed: int, total: int, **kwargs) -> None:
        """Initialize progress bar.

        Args:
            completed: Number of completed tasks
            total: Total number of tasks
        """
        super().__init__(**kwargs)
        self.completed = completed
        self.total = total

    def render(self) -> str:
        """Render the progress bar."""
        if self.total == 0:
            percentage = 0.0
        else:
            percentage = (self.completed / self.total) * 100

        # Create a visual progress bar
        bar_width = 40
        filled = int((self.completed / self.total) * bar_width) if self.total > 0 else 0
        empty = bar_width - filled

        # Color based on progress
        if percentage >= 75:
            bar_color = "green"
        elif percentage >= 50:
            bar_color = "yellow"
        elif percentage >= 25:
            bar_color = "blue"
        else:
            bar_color = "red"

        bar = f"[{bar_color}]{'█' * filled}[/]{'░' * empty}"

        return f"{bar} [{bar_color}]{percentage:5.1f}%[/] ({self.completed}/{self.total})"


class CalendarApp(App):
    """A Textual app for displaying and managing a daily schedule."""

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary;
        color: $text;
        dock: top;
    }

    Footer {
        background: $panel;
        dock: bottom;
    }

    #calendar-container {
        height: 100%;
    }

    #schedule-header {
        background: $panel;
        color: $text;
        padding: 1 2;
        border: heavy $primary;
        margin: 1 1 0 1;
    }

    #progress-container {
        background: $panel-darken-1;
        padding: 1 2;
        margin: 0 1 1 1;
        border: solid $primary-lighten-1;
    }

    #task-list-container {
        height: 1fr;
        padding: 0 1 1 1;
    }

    #task-list {
        height: 100%;
        border: heavy $primary;
    }

    ListView {
        background: $surface;
    }

    ListItem {
        padding: 1 2;
        margin: 0 0 1 0;
        border-bottom: solid $surface-lighten-1;
    }

    ListItem:hover {
        background: $primary-darken-2;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("space", "toggle_complete", "Toggle"),
        ("enter", "toggle_complete", "Toggle"),
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
    ]

    current_time: reactive[dt.time] = reactive(dt.datetime.now().time)

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
            # Schedule info header
            yield Static(self._render_schedule_header(), id="schedule-header")

            # Progress bar section
            with Container(id="progress-container"):
                yield Static(self._render_progress(), id="progress-bar")

            # Task list with container
            with Container(id="task-list-container"):
                yield ListView(id="task-list")

        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount."""
        # Load schedule
        try:
            self._load_schedule()
        except (ScheduleParseError, StateManagerError) as e:
            self.exit(message=f"Error loading schedule: {e}")
            return

        # Populate task list
        self._populate_task_list()

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

    def _populate_task_list(self) -> None:
        """Populate the task list with tasks."""
        if not self.schedule:
            return

        task_list = self.query_one("#task-list", ListView)
        task_list.clear()

        # Get completion state
        state = self.state_manager.load_state()
        completed_tasks = state.completed_tasks if state else set()

        # Get current task and time
        current_task = self.schedule.get_current_task(self.current_time)

        # Add tasks to list
        for task in self.schedule.tasks:
            is_current = current_task is not None and task.id == current_task.id
            is_completed = task.id in completed_tasks
            is_past = task.get_end_time() < self.current_time

            task_item = TaskListItem(
                task,
                is_current=is_current,
                is_completed=is_completed,
                is_past=is_past,
            )
            task_list.append(task_item)

    def _render_schedule_header(self) -> str:
        """Render the schedule header."""
        if not self.schedule:
            return "[yellow]No schedule loaded[/]"

        # Current time
        now = dt.datetime.now()
        time_str = now.strftime("%H:%M:%S")
        day_str = self.schedule.date.strftime("%A, %B %d, %Y")

        # Current task
        current_task = self.schedule.get_current_task(now.time())
        if current_task:
            current_str = f"[bold yellow]▶ {current_task.title}[/]"
            time_left = self._time_until(current_task.get_end_time())
            current_str += f" [dim](ends in {time_left})[/]"
        else:
            # Show next task
            upcoming = self.schedule.get_upcoming_tasks(now.time(), limit=1)
            if upcoming:
                next_task = upcoming[0]
                time_until = self._time_until(next_task.get_start_time())
                current_str = f"[dim]Next: [bold]{next_task.title}[/] in {time_until}[/]"
            else:
                current_str = "[dim]No more tasks today[/]"

        # Build header
        header_lines = [
            f"📅 [bold cyan]{day_str}[/]",
            f"🕐 Current time: [bold yellow]{time_str}[/]",
            f"   {current_str}",
        ]

        return "\n".join(header_lines)

    def _render_progress(self) -> str:
        """Render the progress section."""
        if not self.schedule:
            return ""

        # Get completion stats
        state = self.state_manager.load_state()
        if state:
            completed = len(state.completed_tasks)
            total = len(self.schedule.tasks)
        else:
            completed = 0
            total = len(self.schedule.tasks)

        # Create progress bar
        progress_bar = DayProgressBar(completed, total)
        bar_render = progress_bar.render()

        # Help text
        help_text = "[dim]↑↓/jk: Navigate  │  Space/Enter: Toggle  │  r: Refresh  │  q: Quit[/]"

        return f"[bold]Progress:[/] {bar_render}\n{help_text}"

    def _time_until(self, target_time: dt.time) -> str:
        """Calculate human-readable time until target time.

        Args:
            target_time: The target time

        Returns:
            Human-readable string like "1h 23m"
        """
        now = dt.datetime.now().time()
        now_minutes = now.hour * 60 + now.minute
        target_minutes = target_time.hour * 60 + target_time.minute

        diff_minutes = target_minutes - now_minutes

        if diff_minutes < 0:
            # Past time
            diff_minutes = abs(diff_minutes)
            hours = diff_minutes // 60
            mins = diff_minutes % 60
            if hours > 0:
                return f"{hours}h {mins}m ago" if mins > 0 else f"{hours}h ago"
            return f"{mins}m ago"
        else:
            hours = diff_minutes // 60
            mins = diff_minutes % 60
            if hours > 0:
                return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
            return f"{mins}m"

    def _update_current_time(self) -> None:
        """Update the current time and refresh display."""
        self.current_time = dt.datetime.now().time()

        # Update header
        header_widget = self.query_one("#schedule-header", Static)
        header_widget.update(self._render_schedule_header())

        # Update progress
        progress_widget = self.query_one("#progress-bar", Static)
        progress_widget.update(self._render_progress())

        # Refresh task list
        self._populate_task_list()

    def action_refresh(self) -> None:
        """Manually refresh the schedule."""
        try:
            self._load_schedule()
            self._populate_task_list()
            self._update_current_time()
            self.notify("Schedule refreshed! ✓", severity="information")
        except (ScheduleParseError, StateManagerError) as e:
            self.notify(f"Error refreshing: {e}", severity="error")

    def action_toggle_complete(self) -> None:
        """Toggle completion status of selected task."""
        task_list = self.query_one("#task-list", ListView)

        # Get selected item
        if task_list.index is None:
            self.notify("No task selected", severity="warning")
            return

        selected_item = task_list.highlighted_child
        if not isinstance(selected_item, TaskListItem):
            return

        task = selected_item.task

        # Toggle completion in state
        try:
            if selected_item.is_completed:
                self.state_manager.mark_task_incomplete(task.id)
                self.notify(f"Unmarked: {task.title}", severity="information")
            else:
                self.state_manager.mark_task_complete(task.id)
                self.notify(f"Completed: {task.title} ✓", severity="information", title="Success")

            # Refresh display
            self._populate_task_list()
            self._update_current_time()

            # Restore selection position
            if task_list.index is not None:
                task_list.index = min(task_list.index, len(task_list) - 1)

        except StateManagerError as e:
            self.notify(f"Error updating task: {e}", severity="error")

    def action_cursor_down(self) -> None:
        """Move cursor down (vim-style j)."""
        task_list = self.query_one("#task-list", ListView)
        task_list.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up (vim-style k)."""
        task_list = self.query_one("#task-list", ListView)
        task_list.action_cursor_up()

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
