"""Command-line interface for terminal calendar."""

import datetime as dt
import sys
from pathlib import Path

import click

from .models import AppState
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


if __name__ == "__main__":
    main()
