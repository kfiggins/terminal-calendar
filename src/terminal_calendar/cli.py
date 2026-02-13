"""Command-line interface for terminal calendar."""

import datetime as dt
import sys
from pathlib import Path

import click

from .calendar_app import run_calendar_app
from .models import AppState
from .report_generator import generate_report, save_report, get_recent_reports
from .schedule_parser import ScheduleParseError, load_schedule
from .state_manager import StateManager, StateManagerError


@click.group()
@click.version_option(version="0.1.0", prog_name="tcal")
def main() -> None:
    """Terminal Calendar - AI-generated schedule viewer and tracker.

    A beautiful terminal-based calendar that displays your daily schedule
    with real-time updates and task completion tracking.
    """
    pass


@main.command()
@click.argument("schedule_file", type=click.Path(exists=True, path_type=Path))
def load(schedule_file: Path) -> None:
    """Load a schedule file and save it to state.

    SCHEDULE_FILE: Path to the JSON schedule file to load
    """
    try:
        # Parse the schedule
        click.echo(f"Loading schedule from {schedule_file}...")
        schedule = load_schedule(schedule_file)

        # Create state manager
        state_manager = StateManager()

        # Create new app state
        state = AppState(
            schedule_file=str(schedule_file.absolute()),
            schedule_date=schedule.date,
        )

        # Save state
        state_manager.save_state(state)

        # Display success message
        click.secho("✓ Schedule loaded successfully!", fg="green", bold=True)
        click.echo(f"  Date: {schedule.date}")
        click.echo(f"  Tasks: {len(schedule.tasks)}")
        click.echo(f"  State saved to: {state_manager.get_state_file_path()}")

        # Show first few tasks
        if schedule.tasks:
            click.echo("\n  First tasks:")
            for task in schedule.tasks[:3]:
                click.echo(f"    • {task.start_time} - {task.title}")
            if len(schedule.tasks) > 3:
                click.echo(f"    ... and {len(schedule.tasks) - 3} more")

    except ScheduleParseError as e:
        click.secho(f"✗ Error loading schedule: {e}", fg="red", err=True)
        sys.exit(1)
    except StateManagerError as e:
        click.secho(f"✗ Error saving state: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"✗ Unexpected error: {e}", fg="red", err=True)
        sys.exit(1)


@main.command()
def info() -> None:
    """Show information about the currently loaded schedule."""
    try:
        # Load state
        state_manager = StateManager()
        state = state_manager.load_state()

        if state is None:
            click.secho("✗ No schedule loaded.", fg="yellow")
            click.echo("  Load a schedule with: tcal load <schedule_file>")
            sys.exit(1)

        # Load the schedule file
        schedule = load_schedule(state.schedule_file)

        # Display schedule information
        click.secho("📅 Current Schedule", fg="cyan", bold=True)
        click.echo(f"  Date: {schedule.date}")
        click.echo(f"  File: {state.schedule_file}")
        click.echo(f"  Total tasks: {len(schedule.tasks)}")

        # Completion stats
        completed_count = len(state.completed_tasks)
        completion_pct = state.get_completion_percentage(len(schedule.tasks))
        click.echo(f"  Completed: {completed_count}/{len(schedule.tasks)} ({completion_pct:.0f}%)")

        # Show all tasks with status
        if schedule.tasks:
            click.echo("\n  Tasks:")
            for task in schedule.tasks:
                status = "✓" if state.is_complete(task.id) else "○"
                color = "green" if state.is_complete(task.id) else "white"
                priority_color = {
                    "high": "red",
                    "medium": "yellow",
                    "low": "green",
                }.get(task.priority, "white")

                click.echo(
                    f"    {status} {task.start_time}-{task.end_time} "
                    + click.style(task.title, fg=color)
                    + f" [{click.style(task.priority, fg=priority_color)}]"
                )
                if task.description:
                    click.echo(f"      {task.description[:60]}...")

        # Last updated
        click.echo(f"\n  Last updated: {state.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")

    except StateManagerError as e:
        click.secho(f"✗ Error loading state: {e}", fg="red", err=True)
        sys.exit(1)
    except ScheduleParseError as e:
        click.secho(f"✗ Error loading schedule: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"✗ Unexpected error: {e}", fg="red", err=True)
        sys.exit(1)


@main.command()
@click.argument("task_id")
@click.option(
    "--undo",
    "-u",
    is_flag=True,
    help="Mark task as incomplete instead of complete",
)
def complete(task_id: str, undo: bool) -> None:
    """Mark a task as complete (or incomplete with --undo).

    TASK_ID: The ID of the task to mark as complete
    """
    try:
        # Load state
        state_manager = StateManager()
        state = state_manager.load_state()

        if state is None:
            click.secho("✗ No schedule loaded.", fg="yellow")
            click.echo("  Load a schedule with: tcal load <schedule_file>")
            sys.exit(1)

        # Load schedule to verify task exists
        schedule = load_schedule(state.schedule_file)
        task = schedule.get_task_by_id(task_id)

        if task is None:
            click.secho(f"✗ Task '{task_id}' not found in schedule.", fg="red", err=True)
            # Show available task IDs
            click.echo("\n  Available task IDs:")
            for t in schedule.tasks[:10]:
                click.echo(f"    • {t.id} - {t.title}")
            if len(schedule.tasks) > 10:
                click.echo(f"    ... and {len(schedule.tasks) - 10} more")
            sys.exit(1)

        # Mark complete or incomplete
        if undo:
            state_manager.mark_task_incomplete(task_id)
            click.secho(f"✓ Task '{task.title}' marked as incomplete", fg="yellow")
        else:
            state_manager.mark_task_complete(task_id)
            click.secho(f"✓ Task '{task.title}' marked as complete!", fg="green", bold=True)

        # Show updated completion stats
        state = state_manager.load_state()
        if state:
            completed = len(state.completed_tasks)
            total = len(schedule.tasks)
            pct = state.get_completion_percentage(total)
            click.echo(f"  Progress: {completed}/{total} tasks ({pct:.0f}%)")

    except StateManagerError as e:
        click.secho(f"✗ Error: {e}", fg="red", err=True)
        sys.exit(1)
    except ScheduleParseError as e:
        click.secho(f"✗ Error loading schedule: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"✗ Unexpected error: {e}", fg="red", err=True)
        sys.exit(1)


@main.command()
def clear() -> None:
    """Clear the current schedule and state (use with caution)."""
    try:
        state_manager = StateManager()

        if not state_manager.state_exists():
            click.secho("No state to clear.", fg="yellow")
            return

        # Confirm with user
        if click.confirm("Are you sure you want to clear the current schedule and state?"):
            state_manager.clear_state()
            click.secho("✓ State cleared successfully!", fg="green")
        else:
            click.echo("Cancelled.")

    except StateManagerError as e:
        click.secho(f"✗ Error: {e}", fg="red", err=True)
        sys.exit(1)


@main.command()
def status() -> None:
    """Quick status check - show current task and upcoming tasks."""
    try:
        # Load state
        state_manager = StateManager()
        state = state_manager.load_state()

        if state is None:
            click.secho("✗ No schedule loaded.", fg="yellow")
            click.echo("  Load a schedule with: tcal load <schedule_file>")
            sys.exit(1)

        # Load schedule
        schedule = load_schedule(state.schedule_file)
        current_time = dt.datetime.now().time()

        # Display header
        click.secho(f"📅 {schedule.date.strftime('%A, %B %d, %Y')}", fg="cyan", bold=True)
        click.echo(f"   Current time: {current_time.strftime('%H:%M')}")

        # Show current task
        current_task = schedule.get_current_task(current_time)
        if current_task:
            status = "✓" if state.is_complete(current_task.id) else "○"
            click.secho(f"\n▶ Current Task {status}", fg="yellow", bold=True)
            click.echo(f"   {current_task.start_time}-{current_task.end_time} {current_task.title}")
            if current_task.description:
                click.echo(f"   {current_task.description}")
        else:
            click.secho("\n○ No current task", fg="white")

        # Show upcoming tasks
        upcoming = schedule.get_upcoming_tasks(current_time, limit=3)
        if upcoming:
            click.secho("\n⏰ Upcoming Tasks", fg="blue", bold=True)
            for task in upcoming:
                status = "✓" if state.is_complete(task.id) else "○"
                click.echo(f"   {status} {task.start_time} {task.title}")

        # Show completion
        completed = len(state.completed_tasks)
        total = len(schedule.tasks)
        pct = state.get_completion_percentage(total)
        click.echo(f"\n   Progress: {completed}/{total} tasks ({pct:.0f}%)")

    except StateManagerError as e:
        click.secho(f"✗ Error loading state: {e}", fg="red", err=True)
        sys.exit(1)
    except ScheduleParseError as e:
        click.secho(f"✗ Error loading schedule: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"✗ Unexpected error: {e}", fg="red", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--file",
    "-f",
    "schedule_file",
    type=click.Path(exists=True, path_type=Path),
    help="Schedule file to load (overrides saved state)",
)
def view(schedule_file: Path | None = None) -> None:
    """Launch the interactive TUI calendar view.

    Opens a beautiful terminal interface showing your schedule with
    real-time updates, current task highlighting, and completion tracking.

    Press 'q' to quit, 'r' to refresh.
    """
    try:
        # Check if we have a schedule (either from file or state)
        if schedule_file is None:
            state_manager = StateManager()
            if not state_manager.state_exists():
                click.secho("✗ No schedule loaded.", fg="yellow")
                click.echo("  Load a schedule first with: tcal load <schedule_file>")
                click.echo("  Or specify a file: tcal view --file <schedule_file>")
                sys.exit(1)

        # Launch the TUI
        run_calendar_app(schedule_file=schedule_file)

    except Exception as e:
        click.secho(f"✗ Error: {e}", fg="red", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--date",
    "-d",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Generate report for a specific date (YYYY-MM-DD)",
)
@click.option(
    "--save/--no-save",
    default=True,
    help="Save report to file (default: yes)",
)
@click.option(
    "--open",
    "-o",
    "open_file",
    is_flag=True,
    help="Open the report file after generation",
)
def report(date: dt.datetime | None, save: bool, open_file: bool) -> None:
    """Generate an end-of-day productivity report.

    Shows completion statistics, time analysis, and task breakdown.
    Reports are saved to ~/.terminal-calendar/reports/ by default.
    """
    try:
        # Load state
        state_manager = StateManager()
        state = state_manager.load_state()

        if state is None:
            click.secho("✗ No schedule loaded.", fg="yellow")
            click.echo("  Load a schedule first with: tcal load <schedule_file>")
            sys.exit(1)

        # Load schedule
        schedule = load_schedule(state.schedule_file)

        # Check if date matches (if specified)
        if date and schedule.date != date.date():
            click.secho(
                f"✗ Schedule date ({schedule.date}) doesn't match requested date ({date.date()})",
                fg="red",
                err=True,
            )
            sys.exit(1)

        # Generate report
        report_content = generate_report(schedule, state)

        # Display report
        click.echo(report_content)

        # Save report if requested
        if save:
            reports_dir = state_manager.create_reports_dir()
            report_path = save_report(schedule, state, reports_dir)
            click.echo()
            click.secho(f"✓ Report saved to: {report_path}", fg="green", bold=True)

            # Open file if requested
            if open_file:
                click.launch(str(report_path))
                click.echo(f"  Opened report in default editor")

    except StateManagerError as e:
        click.secho(f"✗ Error: {e}", fg="red", err=True)
        sys.exit(1)
    except ScheduleParseError as e:
        click.secho(f"✗ Error loading schedule: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"✗ Unexpected error: {e}", fg="red", err=True)
        sys.exit(1)


@main.command()
def reports() -> None:
    """List recent reports."""
    try:
        state_manager = StateManager()
        reports_dir = state_manager.config_dir / "reports"

        if not reports_dir.exists():
            click.secho("No reports found.", fg="yellow")
            click.echo(f"  Generate a report with: tcal report")
            return

        recent = get_recent_reports(reports_dir, limit=10)

        if not recent:
            click.secho("No reports found.", fg="yellow")
            return

        click.secho("📊 Recent Reports", fg="cyan", bold=True)
        click.echo()

        for report_path in recent:
            # Get file stats
            stat = report_path.stat()
            modified = dt.datetime.fromtimestamp(stat.st_mtime)
            size = stat.st_size

            # Format display
            date_str = report_path.stem  # Filename without extension
            modified_str = modified.strftime("%Y-%m-%d %H:%M")

            click.echo(f"  📄 {date_str}")
            click.echo(f"     Modified: {modified_str}  |  Size: {size} bytes")
            click.echo(f"     Path: {report_path}")
            click.echo()

    except Exception as e:
        click.secho(f"✗ Error: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
