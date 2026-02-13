"""Statistics and analytics for terminal calendar."""

import datetime as dt
import json
from pathlib import Path
from typing import Dict, List, Tuple

from pydantic import BaseModel

from .models import Schedule, AppState


class DayStats(BaseModel):
    """Statistics for a single day.

    Attributes:
        date: The date
        total_tasks: Total number of tasks
        completed_tasks: Number of completed tasks
        completion_percentage: Completion percentage
        total_minutes: Total scheduled minutes
        completed_minutes: Completed minutes
        high_priority_completed: High priority tasks completed
        high_priority_total: Total high priority tasks
    """

    date: dt.date
    total_tasks: int
    completed_tasks: int
    completion_percentage: float
    total_minutes: int
    completed_minutes: int
    high_priority_completed: int
    high_priority_total: int


def calculate_day_stats(schedule: Schedule, state: AppState) -> DayStats:
    """Calculate statistics for a single day.

    Args:
        schedule: The schedule
        state: The application state

    Returns:
        DayStats object with calculated statistics
    """
    total = len(schedule.tasks)
    completed = len(state.completed_tasks)

    total_minutes = sum(task.duration_minutes() for task in schedule.tasks)
    completed_minutes = sum(
        task.duration_minutes()
        for task in schedule.tasks
        if state.is_complete(task.id)
    )

    high_priority_tasks = [t for t in schedule.tasks if t.priority == "high"]
    high_priority_completed = len([
        t for t in high_priority_tasks
        if state.is_complete(t.id)
    ])

    return DayStats(
        date=schedule.date,
        total_tasks=total,
        completed_tasks=completed,
        completion_percentage=state.get_completion_percentage(total),
        total_minutes=total_minutes,
        completed_minutes=completed_minutes,
        high_priority_completed=high_priority_completed,
        high_priority_total=len(high_priority_tasks),
    )


def analyze_productivity_trends(
    reports_dir: Path,
    days: int = 7,
) -> Dict[str, any]:
    """Analyze productivity trends from recent reports.

    Args:
        reports_dir: Directory containing report files
        days: Number of days to analyze

    Returns:
        Dictionary with trend statistics
    """
    if not reports_dir.exists():
        return {
            "error": "No reports directory found",
            "days_analyzed": 0,
        }

    # Get recent report files
    report_files = sorted(
        reports_dir.glob("*.txt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:days]

    if not report_files:
        return {
            "error": "No reports found",
            "days_analyzed": 0,
        }

    # Parse basic stats from reports
    daily_completions = []
    for report_file in report_files:
        try:
            content = report_file.read_text()
            # Extract completion percentage from report
            for line in content.split("\n"):
                if "Completed:" in line and "(" in line:
                    # Parse "Completed:        X (Y%)" format
                    parts = line.split("(")
                    if len(parts) > 1:
                        pct_str = parts[1].split("%")[0]
                        try:
                            pct = float(pct_str)
                            daily_completions.append(pct)
                            break
                        except ValueError:
                            pass
        except Exception:
            continue

    if not daily_completions:
        return {
            "error": "Could not parse reports",
            "days_analyzed": 0,
        }

    # Calculate trends
    avg_completion = sum(daily_completions) / len(daily_completions)
    max_completion = max(daily_completions)
    min_completion = min(daily_completions)

    # Calculate trend direction
    if len(daily_completions) >= 2:
        recent_avg = sum(daily_completions[:3]) / min(3, len(daily_completions))
        older_avg = sum(daily_completions[3:]) / max(1, len(daily_completions) - 3) if len(daily_completions) > 3 else recent_avg

        if recent_avg > older_avg + 5:
            trend = "improving"
        elif recent_avg < older_avg - 5:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"

    return {
        "days_analyzed": len(daily_completions),
        "average_completion": round(avg_completion, 1),
        "max_completion": round(max_completion, 1),
        "min_completion": round(min_completion, 1),
        "trend": trend,
        "daily_completions": [round(c, 1) for c in daily_completions],
    }


def generate_statistics_report(reports_dir: Path, days: int = 7) -> str:
    """Generate a formatted statistics report.

    Args:
        reports_dir: Directory containing reports
        days: Number of days to analyze

    Returns:
        Formatted statistics report
    """
    stats = analyze_productivity_trends(reports_dir, days)

    if "error" in stats:
        return f"⚠️  {stats['error']}"

    lines = [
        "=" * 70,
        f"PRODUCTIVITY STATISTICS - Last {stats['days_analyzed']} Days",
        "=" * 70,
        "",
        "OVERVIEW",
        "-" * 70,
        f"Average Completion:  {stats['average_completion']}%",
        f"Best Day:            {stats['max_completion']}%",
        f"Lowest Day:          {stats['min_completion']}%",
        "",
    ]

    # Trend analysis
    trend_emoji = {
        "improving": "📈",
        "declining": "📉",
        "stable": "➡️",
        "insufficient_data": "❓",
    }

    trend_msg = {
        "improving": "Productivity is improving! Keep it up!",
        "declining": "Productivity trending down. Consider adjusting your schedule.",
        "stable": "Productivity is consistent.",
        "insufficient_data": "Need more data for trend analysis.",
    }

    lines.extend([
        "TREND ANALYSIS",
        "-" * 70,
        f"Trend: {trend_emoji.get(stats['trend'], '')} {trend_msg.get(stats['trend'], '')}",
        "",
    ])

    # Daily breakdown
    lines.extend([
        "DAILY COMPLETIONS",
        "-" * 70,
    ])

    for i, completion in enumerate(stats['daily_completions']):
        day_label = f"Day -{i}" if i > 0 else "Today"
        bar_length = int(completion / 2)  # Scale to 50 chars max
        bar = "█" * bar_length
        lines.append(f"{day_label:8}  {bar} {completion}%")

    lines.extend([
        "",
        "=" * 70,
    ])

    return "\n".join(lines)
