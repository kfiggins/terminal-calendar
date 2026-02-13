"""Tests for report generation functionality."""

import datetime as dt
from pathlib import Path
import tempfile

import pytest

from terminal_calendar.models import Schedule, Task, AppState
from terminal_calendar.report_generator import (
    generate_report,
    save_report,
    get_recent_reports,
)


@pytest.fixture
def sample_schedule() -> Schedule:
    """Create a sample schedule for testing."""
    return Schedule(
        date=dt.date(2024, 3, 15),
        tasks=[
            Task(
                id="task1",
                title="Morning Standup",
                start_time="09:00",
                end_time="09:30",
                description="Daily team sync",
                priority="high",
            ),
            Task(
                id="task2",
                title="Code Review",
                start_time="09:30",
                end_time="11:00",
                description="Review pull requests",
                priority="high",
            ),
            Task(
                id="task3",
                title="Lunch Break",
                start_time="12:00",
                end_time="13:00",
                description="Take a break",
                priority="low",
            ),
            Task(
                id="task4",
                title="Feature Development",
                start_time="13:00",
                end_time="16:00",
                description="Work on new feature",
                priority="medium",
            ),
        ],
    )


@pytest.fixture
def empty_state() -> AppState:
    """Create an empty app state."""
    return AppState(
        schedule_file="test.json",
        schedule_date=dt.date(2024, 3, 15),
    )


@pytest.fixture
def partial_state() -> AppState:
    """Create a state with some completed tasks."""
    return AppState(
        schedule_file="test.json",
        schedule_date=dt.date(2024, 3, 15),
        completed_tasks={"task1", "task3"},
    )


@pytest.fixture
def complete_state() -> AppState:
    """Create a state with all tasks completed."""
    return AppState(
        schedule_file="test.json",
        schedule_date=dt.date(2024, 3, 15),
        completed_tasks={"task1", "task2", "task3", "task4"},
    )


class TestGenerateReport:
    """Tests for generate_report function."""

    def test_report_structure(self, sample_schedule: Schedule, empty_state: AppState) -> None:
        """Test that report contains all expected sections."""
        report = generate_report(sample_schedule, empty_state)

        # Check for all major sections
        assert "DAILY PRODUCTIVITY REPORT" in report
        assert "SUMMARY" in report
        assert "TIME ANALYSIS" in report
        assert "PRIORITY BREAKDOWN" in report
        assert "INCOMPLETE TASKS" in report
        assert "INSIGHTS & RECOMMENDATIONS" in report

    def test_report_empty_completion(
        self, sample_schedule: Schedule, empty_state: AppState
    ) -> None:
        """Test report with no completed tasks."""
        report = generate_report(sample_schedule, empty_state)

        # Check summary stats
        assert "Total Tasks:      4" in report
        assert "Completed:        0 (0.0%)" in report
        assert "Incomplete:       4" in report

        # Should not have completed tasks section with tasks listed
        assert "COMPLETED TASKS" not in report or "Morning Standup" not in report

        # Should have all tasks in incomplete section
        assert "Morning Standup" in report
        assert "Code Review" in report

    def test_report_partial_completion(
        self, sample_schedule: Schedule, partial_state: AppState
    ) -> None:
        """Test report with some completed tasks."""
        report = generate_report(sample_schedule, partial_state)

        # Check summary stats
        assert "Total Tasks:      4" in report
        assert "Completed:        2 (50.0%)" in report
        assert "Incomplete:       2" in report

        # Should have both sections
        assert "COMPLETED TASKS ✓" in report
        assert "INCOMPLETE TASKS ○" in report

        # Check task placement
        lines = report.split("\n")
        completed_section = "\n".join(
            lines[lines.index([l for l in lines if "COMPLETED TASKS" in l][0]):]
        )
        assert "Morning Standup" in completed_section
        assert "Lunch Break" in completed_section

    def test_report_complete(
        self, sample_schedule: Schedule, complete_state: AppState
    ) -> None:
        """Test report with all tasks completed."""
        report = generate_report(sample_schedule, complete_state)

        # Check summary stats
        assert "Total Tasks:      4" in report
        assert "Completed:        4 (100.0%)" in report
        assert "Incomplete:       0" in report

        # Should have completed section
        assert "COMPLETED TASKS ✓" in report

        # Should not have incomplete section with tasks
        lines = report.split("\n")
        incomplete_idx = None
        for i, line in enumerate(lines):
            if "INCOMPLETE TASKS" in line:
                incomplete_idx = i
                break

        if incomplete_idx is not None:
            # Check next few lines don't have task content
            next_lines = lines[incomplete_idx + 1:incomplete_idx + 5]
            task_markers = ["○", "Morning Standup", "Code Review"]
            assert not any(marker in " ".join(next_lines) for marker in task_markers)

    def test_time_analysis(
        self, sample_schedule: Schedule, partial_state: AppState
    ) -> None:
        """Test time analysis calculations."""
        report = generate_report(sample_schedule, partial_state)

        # Total time: 0.5h + 1.5h + 1h + 3h = 6h
        assert "Total Scheduled:  6h 0m" in report

        # Completed time: task1 (0.5h) + task3 (1h) = 1.5h = 1h 30m
        assert "Time Completed:   1h 30m" in report

    def test_priority_breakdown(
        self, sample_schedule: Schedule, partial_state: AppState
    ) -> None:
        """Test priority breakdown calculations."""
        report = generate_report(sample_schedule, partial_state)

        # High: 1/2 completed (50%)
        assert "HIGH" in report
        assert "1/2 completed (50%)" in report

        # Medium: 0/1 completed (0%)
        assert "MEDIUM" in report
        assert "0/1 completed (0%)" in report

        # Low: 1/1 completed (100%)
        assert "LOW" in report
        assert "1/1 completed (100%)" in report

    def test_insights_excellent(
        self, sample_schedule: Schedule, complete_state: AppState
    ) -> None:
        """Test insights for excellent performance (≥80%)."""
        report = generate_report(sample_schedule, complete_state)
        assert "🎉 Excellent work!" in report
        assert "✨ All high-priority tasks completed!" in report

    def test_insights_challenging(
        self, sample_schedule: Schedule, empty_state: AppState
    ) -> None:
        """Test insights for low performance (<40%)."""
        report = generate_report(sample_schedule, empty_state)
        assert "💪 Challenging day" in report
        assert "⚠️" in report  # Warning about incomplete high-priority tasks

    def test_priority_badges(
        self, sample_schedule: Schedule, partial_state: AppState
    ) -> None:
        """Test that priority badges are included."""
        report = generate_report(sample_schedule, partial_state)
        assert "!!!" in report  # High priority
        assert "!!" in report  # Medium priority
        assert "!" in report  # Low priority (single !)

    def test_task_durations(
        self, sample_schedule: Schedule, empty_state: AppState
    ) -> None:
        """Test that task durations are displayed."""
        report = generate_report(sample_schedule, empty_state)
        assert "Duration: 30m" in report  # Morning Standup
        assert "Duration: 1h 30m" in report  # Code Review
        assert "Duration: 3h" in report  # Feature Development

    def test_date_formatting(
        self, sample_schedule: Schedule, empty_state: AppState
    ) -> None:
        """Test that date is properly formatted."""
        report = generate_report(sample_schedule, empty_state)
        assert "Friday, March 15, 2024" in report

    def test_descriptions_truncated(self) -> None:
        """Test that long descriptions are truncated."""
        schedule = Schedule(
            date=dt.date(2024, 3, 15),
            tasks=[
                Task(
                    id="task1",
                    title="Long Task",
                    start_time="09:00",
                    end_time="10:00",
                    description="A" * 100,  # Very long description
                    priority="high",
                ),
            ],
        )
        state = AppState(
            schedule_file="test.json",
            schedule_date=dt.date(2024, 3, 15),
        )

        report = generate_report(schedule, state)
        # Should be truncated to 60 chars plus "..."
        assert "A" * 60 + "..." in report


class TestSaveReport:
    """Tests for save_report function."""

    def test_save_report_creates_file(
        self, sample_schedule: Schedule, partial_state: AppState
    ) -> None:
        """Test that save_report creates a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)
            report_path = save_report(sample_schedule, partial_state, reports_dir)

            assert report_path.exists()
            assert report_path.is_file()

    def test_save_report_filename(
        self, sample_schedule: Schedule, partial_state: AppState
    ) -> None:
        """Test that report filename is date-based."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)
            report_path = save_report(sample_schedule, partial_state, reports_dir)

            assert report_path.name == "2024-03-15.txt"

    def test_save_report_content(
        self, sample_schedule: Schedule, partial_state: AppState
    ) -> None:
        """Test that saved report contains correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)
            report_path = save_report(sample_schedule, partial_state, reports_dir)

            content = report_path.read_text(encoding="utf-8")
            assert "DAILY PRODUCTIVITY REPORT" in content
            assert "Morning Standup" in content

    def test_save_report_creates_directory(
        self, sample_schedule: Schedule, partial_state: AppState
    ) -> None:
        """Test that save_report creates reports directory if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir) / "reports"
            assert not reports_dir.exists()

            report_path = save_report(sample_schedule, partial_state, reports_dir)

            assert reports_dir.exists()
            assert report_path.exists()

    def test_save_report_overwrites_existing(
        self, sample_schedule: Schedule
    ) -> None:
        """Test that save_report overwrites existing report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)

            # Save with empty state
            state1 = AppState(
                schedule_file="test.json",
                schedule_date=dt.date(2024, 3, 15),
            )
            report_path1 = save_report(sample_schedule, state1, reports_dir)
            content1 = report_path1.read_text()

            # Save again with completed state
            state2 = AppState(
                schedule_file="test.json",
                schedule_date=dt.date(2024, 3, 15),
                completed_tasks={"task1", "task2", "task3", "task4"},
            )
            report_path2 = save_report(sample_schedule, state2, reports_dir)
            content2 = report_path2.read_text()

            # Should be same file
            assert report_path1 == report_path2

            # Content should be different
            assert "Completed:        0" in content1
            assert "Completed:        4" in content2


class TestGetRecentReports:
    """Tests for get_recent_reports function."""

    def test_get_recent_reports_empty_dir(self) -> None:
        """Test with empty reports directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)
            reports = get_recent_reports(reports_dir, limit=5)

            assert reports == []

    def test_get_recent_reports_nonexistent_dir(self) -> None:
        """Test with nonexistent directory."""
        reports_dir = Path("/nonexistent/path")
        reports = get_recent_reports(reports_dir, limit=5)

        assert reports == []

    def test_get_recent_reports_returns_files(self) -> None:
        """Test that recent reports are returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)

            # Create some report files
            (reports_dir / "2024-03-15.txt").write_text("Report 1")
            (reports_dir / "2024-03-14.txt").write_text("Report 2")
            (reports_dir / "2024-03-13.txt").write_text("Report 3")

            reports = get_recent_reports(reports_dir, limit=5)

            assert len(reports) == 3
            assert all(p.suffix == ".txt" for p in reports)

    def test_get_recent_reports_sorted_by_mtime(self) -> None:
        """Test that reports are sorted by modification time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)

            # Create files with different timestamps
            import time

            file1 = reports_dir / "2024-03-13.txt"
            file1.write_text("Report 1")
            time.sleep(0.01)

            file2 = reports_dir / "2024-03-14.txt"
            file2.write_text("Report 2")
            time.sleep(0.01)

            file3 = reports_dir / "2024-03-15.txt"
            file3.write_text("Report 3")

            reports = get_recent_reports(reports_dir, limit=5)

            # Should be newest first
            assert reports[0].name == "2024-03-15.txt"
            assert reports[1].name == "2024-03-14.txt"
            assert reports[2].name == "2024-03-13.txt"

    def test_get_recent_reports_respects_limit(self) -> None:
        """Test that limit parameter is respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)

            # Create many files
            for i in range(10):
                (reports_dir / f"2024-03-{i+1:02d}.txt").write_text(f"Report {i}")

            reports = get_recent_reports(reports_dir, limit=3)

            assert len(reports) == 3

    def test_get_recent_reports_ignores_non_txt(self) -> None:
        """Test that non-.txt files are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)

            # Create various files
            (reports_dir / "2024-03-15.txt").write_text("Report")
            (reports_dir / "2024-03-14.json").write_text("{}")
            (reports_dir / "notes.md").write_text("# Notes")
            (reports_dir / ".hidden").write_text("hidden")

            reports = get_recent_reports(reports_dir, limit=5)

            assert len(reports) == 1
            assert reports[0].name == "2024-03-15.txt"
