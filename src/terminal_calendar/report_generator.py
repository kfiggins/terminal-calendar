"""Report generation for terminal calendar."""

import datetime as dt
from pathlib import Path

from .models import Schedule, AppState


def generate_report(schedule: Schedule, state: AppState) -> str:
    """Generate an end-of-day report.

    Args:
        schedule: The schedule to report on
        state: The application state with completion data

    Returns:
        Formatted report string
    """
    # Header
    report_lines = [
        "=" * 70,
        f"DAILY PRODUCTIVITY REPORT",
        f"Date: {schedule.date.strftime('%A, %B %d, %Y')}",
        "=" * 70,
        "",
    ]

    # Summary statistics
    total_tasks = len(schedule.tasks)
    completed_tasks = len(state.completed_tasks)
    incomplete_tasks = total_tasks - completed_tasks
    completion_pct = state.get_completion_percentage(total_tasks)

    report_lines.extend([
        "SUMMARY",
        "-" * 70,
        f"Total Tasks:      {total_tasks}",
        f"Completed:        {completed_tasks} ({completion_pct:.1f}%)",
        f"Incomplete:       {incomplete_tasks}",
        "",
    ])

    # Time statistics
    total_time_minutes = sum(task.duration_minutes() for task in schedule.tasks)
    completed_time_minutes = sum(
        task.duration_minutes()
        for task in schedule.tasks
        if task.id in state.completed_tasks
    )

    total_hours = total_time_minutes // 60
    total_mins = total_time_minutes % 60
    completed_hours = completed_time_minutes // 60
    completed_mins = completed_time_minutes % 60

    report_lines.extend([
        "TIME ANALYSIS",
        "-" * 70,
        f"Total Scheduled:  {total_hours}h {total_mins}m",
        f"Time Completed:   {completed_hours}h {completed_mins}m",
        "",
    ])

    # Priority breakdown
    priority_stats = {
        "high": {"total": 0, "completed": 0},
        "medium": {"total": 0, "completed": 0},
        "low": {"total": 0, "completed": 0},
    }

    for task in schedule.tasks:
        priority_stats[task.priority]["total"] += 1
        if task.id in state.completed_tasks:
            priority_stats[task.priority]["completed"] += 1

    report_lines.extend([
        "PRIORITY BREAKDOWN",
        "-" * 70,
    ])

    for priority in ["high", "medium", "low"]:
        stats = priority_stats[priority]
        total = stats["total"]
        completed = stats["completed"]
        if total > 0:
            pct = (completed / total) * 100
            report_lines.append(
                f"{priority.upper():8}  {completed}/{total} completed ({pct:.0f}%)"
            )

    report_lines.append("")

    # Completed tasks
    completed_task_list = [
        task for task in schedule.tasks
        if task.id in state.completed_tasks
    ]

    if completed_task_list:
        report_lines.extend([
            "COMPLETED TASKS ✓",
            "-" * 70,
        ])

        for task in completed_task_list:
            duration = task.duration_minutes()
            hours = duration // 60
            mins = duration % 60
            duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

            priority_marker = {
                "high": "!!!",
                "medium": "!!",
                "low": "!",
            }.get(task.priority, "")

            report_lines.append(
                f"  ✓ {task.start_time}-{task.end_time}  {task.title} {priority_marker}"
            )
            if task.description:
                report_lines.append(f"    {task.description[:60]}...")
            report_lines.append(f"    Duration: {duration_str}")
            report_lines.append("")

    # Incomplete tasks
    incomplete_task_list = [
        task for task in schedule.tasks
        if task.id not in state.completed_tasks
    ]

    if incomplete_task_list:
        report_lines.extend([
            "INCOMPLETE TASKS ○",
            "-" * 70,
        ])

        for task in incomplete_task_list:
            duration = task.duration_minutes()
            hours = duration // 60
            mins = duration % 60
            duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

            priority_marker = {
                "high": "!!!",
                "medium": "!!",
                "low": "!",
            }.get(task.priority, "")

            report_lines.append(
                f"  ○ {task.start_time}-{task.end_time}  {task.title} {priority_marker}"
            )
            if task.description:
                report_lines.append(f"    {task.description[:60]}...")
            report_lines.append(f"    Duration: {duration_str}")
            report_lines.append("")

    # Recommendations
    report_lines.extend([
        "INSIGHTS & RECOMMENDATIONS",
        "-" * 70,
    ])

    insights = []

    if completion_pct >= 80:
        insights.append("🎉 Excellent work! You completed most of your tasks today.")
    elif completion_pct >= 60:
        insights.append("👍 Good progress! You're getting most things done.")
    elif completion_pct >= 40:
        insights.append("📈 Fair progress. Consider breaking tasks into smaller chunks.")
    else:
        insights.append("💪 Challenging day. Focus on high-priority items first tomorrow.")

    # High priority tasks incomplete
    high_priority_incomplete = [
        task for task in incomplete_task_list
        if task.priority == "high"
    ]
    if high_priority_incomplete:
        insights.append(
            f"⚠️  {len(high_priority_incomplete)} high-priority task(s) incomplete - "
            "consider these for tomorrow."
        )

    # All high priority completed
    high_priority_completed = all(
        task.id in state.completed_tasks
        for task in schedule.tasks
        if task.priority == "high"
    )
    if high_priority_completed and priority_stats["high"]["total"] > 0:
        insights.append("✨ All high-priority tasks completed!")

    for insight in insights:
        report_lines.append(f"  {insight}")

    report_lines.extend([
        "",
        "=" * 70,
        f"Report generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 70,
    ])

    return "\n".join(report_lines)


def save_report(
    schedule: Schedule,
    state: AppState,
    reports_dir: Path,
) -> Path:
    """Generate and save a report.

    Args:
        schedule: The schedule to report on
        state: The application state with completion data
        reports_dir: Directory to save reports

    Returns:
        Path to the saved report file
    """
    # Ensure reports directory exists
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Generate report
    report_content = generate_report(schedule, state)

    # Create filename with date
    filename = f"{schedule.date.strftime('%Y-%m-%d')}.txt"
    report_path = reports_dir / filename

    # Save report
    report_path.write_text(report_content, encoding="utf-8")

    return report_path


def get_recent_reports(reports_dir: Path, limit: int = 5) -> list[Path]:
    """Get the most recent report files.

    Args:
        reports_dir: Directory containing reports
        limit: Maximum number of reports to return

    Returns:
        List of report file paths, newest first
    """
    if not reports_dir.exists():
        return []

    # Get all .txt files
    report_files = list(reports_dir.glob("*.txt"))

    # Sort by modification time, newest first
    report_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    return report_files[:limit]
