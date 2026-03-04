"""Configuration — loads from .env, validates."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")
CLAUDE_PATH = os.getenv("CLAUDE_PATH", "/opt/homebrew/bin/claude")
ALLOWED_BASE = Path(os.getenv("ALLOWED_BASE", str(Path.home() / "Documents")))
CLAUDE_TIMEOUT = int(os.getenv("CLAUDE_TIMEOUT", "300"))  # 5 min


def validate():
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_USER_ID:
        missing.append("TELEGRAM_USER_ID")
    if missing:
        sys.exit(f"Missing env vars: {', '.join(missing)}")

    if not Path(CLAUDE_PATH).exists():
        sys.exit(f"Claude CLI not found at {CLAUDE_PATH}")


def allowed_user_ids() -> set[int]:
    return {int(uid.strip()) for uid in TELEGRAM_USER_ID.split(",") if uid.strip()}
