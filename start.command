#!/bin/bash
# Double-click this file to start the Claude TG Bridge bot
cd "$(dirname "$0")"

# Create venv if needed
if [ ! -d .venv ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
fi

unset CLAUDECODE
echo "Starting Claude TG Bridge..."
echo "Press Ctrl+C to stop."
echo ""
.venv/bin/python3 -u bot.py
