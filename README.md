# Terminal Calendar 📅

A beautiful, interactive terminal-based calendar that displays your AI-generated daily schedule with real-time updates, task completion tracking, and end-of-day reporting.

## ✨ Features

- **🤖 LLM-Generated Schedules**: Create schedules from natural language task lists
- **⏰ Real-Time Updates**: Always shows your current task with visual indicators
- **✅ Task Completion**: Mark tasks complete with simple keyboard shortcuts
- **💾 Persistent State**: Close and reopen - your progress is always saved
- **📊 Daily Reports**: Get end-of-day summaries of your productivity
- **🎨 Beautiful UI**: Colorful, easy-to-read terminal interface

## 🚀 Quick Start

> **Note**: This project is under active development. Installation and usage instructions will be updated as features are implemented.

### Prerequisites

- Python 3.11 or higher
- A terminal emulator (iTerm2, Alacritty, or any modern terminal)
- An LLM (like Claude, GPT-4, etc.) to generate your schedules

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/terminal-calendar.git
cd terminal-calendar

# Install with pip (development mode)
pip install -e .

# Or with poetry
poetry install
```

### Basic Usage

1. **Generate a schedule** using your preferred LLM with this prompt:

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

2. **Load your schedule**:
```bash
tcal load my_schedule.json
```

3. **View your calendar**:
```bash
tcal view
```

4. **Generate end-of-day report**:
```bash
tcal report
```

## 🎮 Keyboard Shortcuts

When viewing the calendar:

- `↑/↓` or `j/k` - Navigate tasks
- `Space` or `Enter` - Mark task complete/incomplete
- `r` - Generate report
- `q` or `Ctrl+C` - Quit

## 📁 File Locations

- **Configuration**: `~/.terminal-calendar/config.json`
- **State**: `~/.terminal-calendar/state.json`
- **Reports**: `~/.terminal-calendar/reports/`

## 🛠️ Development

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for the detailed development roadmap and current progress.

### Running Tests

```bash
pytest
```

### Project Structure

```
terminal-calendar/
├── src/terminal_calendar/   # Main application code
├── tests/                    # Test suite
├── examples/                 # Example schedule files
├── CLAUDE.md                # Agent guidance document
└── IMPLEMENTATION.md        # Development roadmap
```

## 🤝 Contributing

Contributions are welcome! Please read the development documentation in [CLAUDE.md](CLAUDE.md) and [IMPLEMENTATION.md](IMPLEMENTATION.md) first.

## 📝 License

MIT License - see LICENSE file for details

## 🎯 Roadmap

- [x] Project setup and documentation
- [ ] Core schedule parsing and validation
- [ ] State management and persistence
- [ ] Basic CLI interface
- [ ] Terminal UI with Textual
- [ ] Interactive task completion
- [ ] Enhanced visual design
- [ ] Report generation
- [ ] Configuration system
- [ ] Advanced features (statistics, exports, etc.)

## 💡 Tips

- **Terminal Recommendation**: iTerm2 works great! If you want alternatives, try Alacritty (fast) or Kitty (feature-rich)
- **Color Support**: Make sure your terminal supports 256 colors for the best experience
- **Schedule Templates**: Save your LLM prompts as templates for consistent schedule generation

---

Built with ❤️ using [Textual](https://textual.textualize.io/)
