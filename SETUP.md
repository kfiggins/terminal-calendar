# Setup Guide

## Installation

### 1. Create and activate virtual environment

```bash
# Create venv (first time only)
python3 -m venv .venv

# Activate venv (do this every time you work on the project)
source .venv/bin/activate
```

### 2. Install the package

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### 3. Verify installation

```bash
# Check the tcal command is available
which tcal

# Test the package import
python -c "import terminal_calendar; print(terminal_calendar.__version__)"
```

## Daily Usage

Every time you open a new terminal to work on this project:

```bash
# Navigate to project directory
cd ~/repos/personal/terminal-calendar

# Activate virtual environment
source .venv/bin/activate

# You should see (.venv) in your prompt
# Now you can use tcal commands and run tests
```

## Development Commands

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=terminal_calendar

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## Deactivate Virtual Environment

When you're done working:

```bash
deactivate
```

## Installation Summary

✅ **Installed Dependencies:**
- textual v7.5.0 - Terminal UI framework
- pydantic v2.12.5 - Data validation
- click v8.3.1 - CLI framework
- python-dateutil v2.9.0 - Date handling
- pytest v9.0.2 - Testing framework
- black v26.1.0 - Code formatter
- ruff v0.15.1 - Fast linter
- mypy v1.19.1 - Type checker

The `tcal` command is now available when the virtual environment is active!
