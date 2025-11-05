#!/bin/bash
source ~/.zprofile

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Script paths relative to project root
PYTHON_SCRIPT="$PROJECT_ROOT/toeic/genToeicQ.py"
DB_PATH="$PROJECT_ROOT/data/toeic.db"
LOG_PATH="$PROJECT_ROOT/toeic/genToeicQ.log"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"

# Run the Python script
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=1 --level=1 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=1 --level=2 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=1 --level=3 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=1 --level=4 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=1 --level=5 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=2 --level=1 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=2 --level=2 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=2 --level=3 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=2 --level=4 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=2 --level=5 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=3 --level=1 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=3 --level=2 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=3 --level=3 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=3 --level=4 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=3 --level=5 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=4 --level=1 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=4 --level=2 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=4 --level=3 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=4 --level=4 --count=5 --db="$DB_PATH"
"$VENV_PYTHON" "$PYTHON_SCRIPT" --part=4 --level=5 --count=5 --db="$DB_PATH"
