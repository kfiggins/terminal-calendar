#!/bin/bash
# Quick launcher for terminal-calendar in development mode
# Usage: ./tcal-dev.sh [tcal commands...]
# Example: ./tcal-dev.sh view

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/.venv/bin/activate"
tcal "$@"
