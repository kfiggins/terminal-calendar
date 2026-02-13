"""Export functionality for terminal calendar."""

import csv
import datetime as dt
import json
from pathlib import Path
from typing import TextIO

from .models import Schedule, AppState


def export_to_ical(schedule: Schedule, output_path: Path) -> None:
    """Export schedule to iCalendar format.

    Args:
        schedule: The schedule to export
        output_path: Path to write the .ics file
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Terminal Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for task in schedule.tasks:
        # Convert to datetime
        start_dt = dt.datetime.combine(schedule.date, task.get_start_time())
        end_dt = dt.datetime.combine(schedule.date, task.get_end_time())

        # Format for iCal (YYYYMMDDTHHMMSS)
        start_str = start_dt.strftime("%Y%m%dT%H%M%S")
        end_str = end_dt.strftime("%Y%m%dT%H%M%S")
        created_str = dt.datetime.now().strftime("%Y%m%dT%H%M%S")

        # Map priority to iCal priority (1=high, 5=medium, 9=low)
        priority_map = {
            "high": "1",
            "medium": "5",
            "low": "9",
        }
        ical_priority = priority_map.get(task.priority, "5")

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{task.id}@terminal-calendar",
            f"DTSTAMP:{created_str}",
            f"DTSTART:{start_str}",
            f"DTEND:{end_str}",
            f"SUMMARY:{task.title}",
            f"DESCRIPTION:{task.description}",
            f"PRIORITY:{ical_priority}",
            "END:VEVENT",
        ])

    lines.extend([
        "END:VCALENDAR",
        "",  # Trailing newline
    ])

    output_path.write_text("\n".join(lines), encoding="utf-8")


def export_to_csv(
    schedule: Schedule,
    output_path: Path,
    state: AppState | None = None,
) -> None:
    """Export schedule to CSV format.

    Args:
        schedule: The schedule to export
        output_path: Path to write the .csv file
        state: Optional state for completion status
    """
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "task_id",
            "title",
            "start_time",
            "end_time",
            "duration_minutes",
            "description",
            "priority",
            "completed",
            "notes_count",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for task in schedule.tasks:
            completed = state.is_complete(task.id) if state else False
            notes_count = len(state.get_notes(task.id)) if state else 0

            writer.writerow({
                "task_id": task.id,
                "title": task.title,
                "start_time": task.start_time,
                "end_time": task.end_time,
                "duration_minutes": task.duration_minutes(),
                "description": task.description,
                "priority": task.priority,
                "completed": "Yes" if completed else "No",
                "notes_count": notes_count,
            })


def export_to_json(
    schedule: Schedule,
    output_path: Path,
    state: AppState | None = None,
    include_notes: bool = True,
) -> None:
    """Export schedule to JSON format with optional state.

    Args:
        schedule: The schedule to export
        output_path: Path to write the .json file
        state: Optional state for completion and notes
        include_notes: Whether to include task notes
    """
    # Start with base schedule data
    data = schedule.model_dump(mode="json")

    # Add state information if provided
    if state:
        # Add completion status to each task
        for task_data in data["tasks"]:
            task_id = task_data["id"]
            task_data["completed"] = state.is_complete(task_id)

            # Add notes if requested
            if include_notes:
                notes = state.get_notes(task_id)
                task_data["notes"] = [
                    {
                        "timestamp": note.timestamp.isoformat(),
                        "content": note.content,
                    }
                    for note in notes
                ]

    # Write to file
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def export_report_to_csv(
    schedule: Schedule,
    state: AppState,
    output_path: Path,
) -> None:
    """Export a summary report to CSV format.

    Args:
        schedule: The schedule to report on
        state: The application state
        output_path: Path to write the .csv file
    """
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        # Summary section
        writer.writerow(["Daily Report Summary"])
        writer.writerow(["Date", schedule.date.strftime("%Y-%m-%d")])
        writer.writerow([])

        # Statistics
        total = len(schedule.tasks)
        completed = len(state.completed_tasks)
        completion_pct = state.get_completion_percentage(total)

        writer.writerow(["Total Tasks", total])
        writer.writerow(["Completed", completed])
        writer.writerow(["Completion %", f"{completion_pct:.1f}%"])
        writer.writerow([])

        # Time analysis
        total_minutes = sum(task.duration_minutes() for task in schedule.tasks)
        completed_minutes = sum(
            task.duration_minutes()
            for task in schedule.tasks
            if state.is_complete(task.id)
        )

        writer.writerow(["Total Time (hours)", f"{total_minutes / 60:.1f}"])
        writer.writerow(["Completed Time (hours)", f"{completed_minutes / 60:.1f}"])
        writer.writerow([])

        # Priority breakdown
        writer.writerow(["Priority Breakdown"])
        writer.writerow(["Priority", "Total", "Completed", "Completion %"])

        for priority in ["high", "medium", "low"]:
            priority_tasks = [t for t in schedule.tasks if t.priority == priority]
            priority_completed = len([
                t for t in priority_tasks
                if state.is_complete(t.id)
            ])
            priority_total = len(priority_tasks)
            priority_pct = (priority_completed / priority_total * 100) if priority_total > 0 else 0

            writer.writerow([
                priority.capitalize(),
                priority_total,
                priority_completed,
                f"{priority_pct:.0f}%",
            ])

        writer.writerow([])

        # Task details
        writer.writerow(["Task Details"])
        writer.writerow([
            "Task ID",
            "Title",
            "Start",
            "End",
            "Duration",
            "Priority",
            "Completed",
            "Notes",
        ])

        for task in schedule.tasks:
            completed_str = "Yes" if state.is_complete(task.id) else "No"
            notes = state.get_notes(task.id)
            notes_str = f"{len(notes)} note(s)" if notes else "No notes"

            writer.writerow([
                task.id,
                task.title,
                task.start_time,
                task.end_time,
                f"{task.duration_minutes()}m",
                task.priority,
                completed_str,
                notes_str,
            ])


def export_report_to_json(
    schedule: Schedule,
    state: AppState,
    output_path: Path,
) -> None:
    """Export a summary report to JSON format.

    Args:
        schedule: The schedule to report on
        state: The application state
        output_path: Path to write the .json file
    """
    total = len(schedule.tasks)
    completed = len(state.completed_tasks)

    # Calculate statistics
    total_minutes = sum(task.duration_minutes() for task in schedule.tasks)
    completed_minutes = sum(
        task.duration_minutes()
        for task in schedule.tasks
        if state.is_complete(task.id)
    )

    # Priority breakdown
    priority_stats = {}
    for priority in ["high", "medium", "low"]:
        priority_tasks = [t for t in schedule.tasks if t.priority == priority]
        priority_completed = len([
            t for t in priority_tasks
            if state.is_complete(t.id)
        ])
        priority_total = len(priority_tasks)

        priority_stats[priority] = {
            "total": priority_total,
            "completed": priority_completed,
            "completion_percentage": (priority_completed / priority_total * 100) if priority_total > 0 else 0,
        }

    # Build report
    report = {
        "date": schedule.date.isoformat(),
        "summary": {
            "total_tasks": total,
            "completed_tasks": completed,
            "incomplete_tasks": total - completed,
            "completion_percentage": state.get_completion_percentage(total),
        },
        "time_analysis": {
            "total_hours": total_minutes / 60,
            "completed_hours": completed_minutes / 60,
        },
        "priority_breakdown": priority_stats,
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "start_time": task.start_time,
                "end_time": task.end_time,
                "duration_minutes": task.duration_minutes(),
                "priority": task.priority,
                "completed": state.is_complete(task.id),
                "notes": [
                    {
                        "timestamp": note.timestamp.isoformat(),
                        "content": note.content,
                    }
                    for note in state.get_notes(task.id)
                ],
            }
            for task in schedule.tasks
        ],
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
