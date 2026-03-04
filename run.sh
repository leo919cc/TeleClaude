#!/bin/bash
cd "$(dirname "$0")"
unset CLAUDECODE
exec .venv/bin/python3 -u bot.py 2>&1
