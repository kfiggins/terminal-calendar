# Terminal Calendar 📅

A beautiful, interactive terminal-based calendar that displays your AI-generated daily schedule with real-time updates, task completion tracking, and end-of-day reporting.

## ✨ Features

- **🤖 LLM-Generated Schedules**: Create schedules from natural language task lists using JSON
- **⏰ Real-Time Updates**: Auto-refreshes every minute with current task highlighting
- **✅ Task Completion**: Mark tasks complete with simple keyboard shortcuts
- **💾 Persistent State**: Close and reopen - your progress is always saved
- **📊 Daily Reports**: Comprehensive end-of-day summaries with insights and recommendations
- **🎨 Beautiful UI**: Colorful, priority-coded terminal interface with progress bars
- **⌨️  Vim-Style Navigation**: Navigate with hjkl or arrow keys

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- A terminal emulator with 256-color support (iTerm2, Alacritty, or any modern terminal)
- An LLM (like Claude, GPT-4, etc.) to generate your schedules

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/terminal-calendar.git
cd terminal-calendar

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Verify installation
tcal --version
```

### Basic Usage

#### 1. Generate a Schedule with an LLM

Use your preferred LLM (Claude, GPT-4, etc.) with this prompt:

```
Create a daily schedule in JSON format for the following tasks:
- Morning standup at 9am (15 minutes)
- Deep work session on project X (2 hours)
- Lunch break (1 hour)
- Client meeting (30 minutes)
- Code review (1 hour)
- Email and admin tasks (30 minutes)

Format the output as JSON with this structure:
{
  "date": "YYYY-MM-DD",
  "tasks": [
    {
      "id": "task_1",
      "title": "Task name",
      "start_time": "HH:MM",
      "end_time": "HH:MM",
      "description": "Brief description",
      "priority": "high|medium|low"
    }
  ]
}
```

Save the JSON output to a file (e.g., `schedule.json`). See [examples/schedule.json](examples/schedule.json) for a complete example.

#### 2. Load Your Schedule

```bash
tcal load schedule.json
```

This loads your schedule and saves it to the application state at `~/.terminal-calendar/state.json`.

#### 3. View Your Calendar

```bash
tcal view
```

Launches the interactive TUI with:
- Current task highlighted in yellow with time remaining
- Color-coded priority badges (!!!  = high, !! = medium, ! = low)
- Progress bar showing completion percentage
- Auto-refresh every minute
- Task durations and descriptions

#### 4. Mark Tasks Complete

Within the TUI:
- Use `↑/↓` or `j/k` to navigate
- Press `Space` or `Enter` to toggle task completion
- Completed tasks show a green ✓ checkmark

Or from the command line:
```bash
tcal complete task_1        # Mark complete
tcal complete --undo task_1 # Mark incomplete
```

#### 5. Check Your Progress

```bash
tcal status  # Quick overview of current and upcoming tasks
tcal info    # Detailed schedule information
```

#### 6. Generate Reports

```bash
tcal report              # Generate and save report
tcal report --no-save    # Display only, don't save
tcal report --open       # Generate and open in editor
tcal reports             # List recent reports
```

Reports include:
- Completion statistics (overall and by priority)
- Time analysis (scheduled vs completed)
- Task breakdowns (completed and incomplete)
- Actionable insights and recommendations

### All Commands

```bash
tcal load <file>         # Load a schedule file
tcal view                # Launch interactive TUI
tcal view --file <file>  # View specific file without loading

tcal info                # Show schedule information
tcal status              # Quick status check
tcal complete <task_id>  # Mark task complete
tcal complete --undo     # Mark task incomplete

tcal report              # Generate end-of-day report
tcal report --date DATE  # Report for specific date
tcal reports             # List recent reports

tcal clear               # Clear current schedule
tcal --version           # Show version
tcal --help              # Show help
```

## 🎮 Keyboard Shortcuts

When viewing the calendar (`tcal view`):

- `↑/↓` or `j/k` - Navigate through tasks
- `Space` or `Enter` - Toggle task completion status
- `r` - Refresh schedule from file
- `q` - Quit application

**Navigation**: Vim-style (j/k) and arrow keys both work!
**Pro tip**: Use `j` and `k` for one-handed navigation while taking notes

## 📁 File Locations

All application data is stored in `~/.terminal-calendar/`:

- **State**: `~/.terminal-calendar/state.json` - Current schedule and completion status
- **Reports**: `~/.terminal-calendar/reports/YYYY-MM-DD.txt` - Daily productivity reports

The state file contains:
- Path to loaded schedule file
- Schedule date
- Set of completed task IDs
- Last updated timestamp

Reports are automatically saved with date-based filenames for easy organization.

## 🛠️ Development

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for the detailed development roadmap and current progress.

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/yourusername/terminal-calendar.git
cd terminal-calendar

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with development dependencies
pip install -e .
pip install pytest pytest-cov black ruff mypy

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/terminal_calendar --cov-report=term-missing

# Format code
black src/ tests/

# Lint code
ruff src/ tests/

# Type check
mypy src/
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_cli.py

# Run with coverage report
pytest --cov=src/terminal_calendar --cov-report=html
open htmlcov/index.html  # View coverage report
```

**Current Test Status**: 94 tests, 65% coverage
- `models.py`: 96% coverage
- `report_generator.py`: 100% coverage
- `schedule_parser.py`: 91% coverage
- `state_manager.py`: 85% coverage
- `cli.py`: 74% coverage

### Project Structure

```
terminal-calendar/
├── src/terminal_calendar/
│   ├── __init__.py
│   ├── models.py              # Pydantic data models
│   ├── schedule_parser.py     # JSON parsing and validation
│   ├── state_manager.py       # State persistence
│   ├── cli.py                 # Click-based CLI
│   ├── calendar_app.py        # Textual TUI application
│   └── report_generator.py    # Report generation
├── tests/
│   ├── test_cli.py            # CLI integration tests
│   ├── test_report_generator.py
│   ├── test_schedule_parser.py
│   ├── test_state_manager.py
│   └── fixtures/              # Test data
├── examples/
│   └── schedule.json          # Example schedule file
├── CLAUDE.md                  # Agent guidance document
├── IMPLEMENTATION.md          # Detailed development phases
└── pyproject.toml             # Project configuration
```

### Architecture

**Data Flow**:
1. User generates schedule JSON with LLM
2. `schedule_parser` validates and loads JSON into Pydantic models
3. `state_manager` persists completion status to `~/.terminal-calendar/`
4. `cli` provides command interface using Click
5. `calendar_app` displays interactive TUI using Textual
6. `report_generator` creates end-of-day summaries

**Key Technologies**:
- **Textual**: Modern TUI framework with rich widgets
- **Pydantic**: Data validation and parsing
- **Click**: Command-line interface framework
- **pytest**: Testing framework

## 🤝 Contributing

Contributions are welcome! Please read the development documentation in [CLAUDE.md](CLAUDE.md) and [IMPLEMENTATION.md](IMPLEMENTATION.md) first.

## 📝 License

MIT License - see LICENSE file for details

## 🎯 Roadmap

- [x] Project setup and documentation
- [x] Core schedule parsing and validation
- [x] State management and persistence
- [x] Basic CLI interface
- [x] Terminal UI with Textual
- [x] Interactive task completion
- [x] Enhanced visual design with priority colors
- [x] End-of-day report generation
- [x] Comprehensive testing (94 tests, 65% coverage)
- [ ] Configuration system (custom themes, preferences)
- [ ] Advanced features (week/month views, statistics dashboard)
- [ ] Schedule templates and automation
- [ ] Export formats (iCal, CSV)

## 💡 Tips & Best Practices

### Terminal Setup
- **Recommended Terminals**: iTerm2 (macOS), Alacritty (fast), Kitty (feature-rich), Windows Terminal (Windows)
- **Color Support**: Ensure your terminal supports 256 colors for the full experience
- **Font**: Use a nerd font (e.g., Fira Code, JetBrains Mono) for best icon rendering

### Schedule Generation
- **Save Your Prompts**: Keep your LLM prompts as templates for consistent scheduling
- **Be Specific**: Include exact times, durations, and priorities when asking the LLM
- **Buffer Time**: Add 5-10 minute buffers between tasks for transitions
- **Realistic Estimates**: Don't over-schedule - leave breathing room

### Workflow Tips
- **Morning Routine**: Load your schedule first thing: `tcal load schedule.json && tcal view`
- **Keep It Open**: Run `tcal view` in a dedicated terminal tab/pane and check throughout the day
- **Quick Checks**: Use `tcal status` for a quick glance without launching the full TUI
- **End of Day**: Run `tcal report` to review your progress and generate insights

### Priority Guidelines
- **High (!!! red)**: Critical tasks, deadlines, important meetings
- **Medium (!! yellow)**: Regular work, routine tasks
- **Low (! green)**: Optional tasks, nice-to-haves, breaks

### JSON Tips
- **Task IDs**: Use descriptive IDs like `standup_morning` instead of `task1`
- **Descriptions**: Keep descriptions concise but informative (they show under each task)
- **Time Format**: Always use 24-hour format (HH:MM) like "09:00", "14:30"
- **Date Format**: Use ISO format (YYYY-MM-DD) like "2024-03-15"

---

Built with ❤️ using [Textual](https://textual.textualize.io/)
