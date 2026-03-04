"""Async subprocess wrapper for `claude -p`."""

import asyncio
import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from config import CLAUDE_PATH, CLAUDE_TIMEOUT

MEDIA_DIR = Path(tempfile.gettempdir()) / "claude-tg-media"

logger = logging.getLogger(__name__)


@dataclass
class Session:
    project_dir: Path | None = None
    session_id: str | None = None
    model: str | None = None
    total_cost: float = 0.0
    total_duration: float = 0.0
    message_count: int = 0


@dataclass
class ClaudeResult:
    text: str
    cost: float = 0.0
    duration: float = 0.0
    session_id: str | None = None
    is_error: bool = False
    run_started: float = 0.0  # time.time() when the run started


class ClaudeRunner:
    def __init__(self):
        self.sessions: dict[int, Session] = {}  # user_id -> session

    def get_session(self, user_id: int) -> Session:
        if user_id not in self.sessions:
            self.sessions[user_id] = Session()
        return self.sessions[user_id]

    def clear_session(self, user_id: int) -> None:
        self.sessions[user_id] = Session()

    def set_project(self, user_id: int, project_dir: Path) -> None:
        session = self.get_session(user_id)
        session.project_dir = project_dir
        session.session_id = None  # Reset session for new project

    async def run(self, user_id: int, prompt: str) -> ClaudeResult:
        session = self.get_session(user_id)

        cmd = [CLAUDE_PATH, "-p", "--output-format", "json"]
        # Allow Claude to read files from the media temp directory
        if MEDIA_DIR.is_dir():
            cmd.extend(["--add-dir", str(MEDIA_DIR)])
        if session.model:
            cmd.extend(["--model", session.model])
        if session.session_id:
            cmd.extend(["--resume", session.session_id])

        # Build env: ensure HOME/USER are set (LaunchAgent has minimal env),
        # and remove CLAUDECODE to avoid nested session detection
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        env.setdefault("HOME", str(Path.home()))
        env.setdefault("USER", os.getlogin())
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
        cwd = None
        if session.project_dir:
            cwd = str(session.project_dir)

        logger.info("Running: %s (cwd=%s)", " ".join(cmd[:4]), cwd)
        run_started = time.time()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=prompt.encode()),
                timeout=CLAUDE_TIMEOUT,
            )

            raw_out = stdout.decode().strip()
            raw_err = stderr.decode().strip()
            logger.info("claude exit=%d, stdout=%d bytes, stderr=%d bytes", proc.returncode, len(raw_out), len(raw_err))
            if raw_err:
                logger.warning("claude stderr: %s", raw_err[:500])

            if proc.returncode != 0:
                err = raw_err or raw_out
                return ClaudeResult(text=f"Error (exit {proc.returncode}):\n{err}", is_error=True)

            result = self._parse_output(raw_out)
            result.run_started = run_started
            session.message_count += 1
            session.total_cost += result.cost
            session.total_duration += result.duration
            return result

        except asyncio.TimeoutError:
            proc.kill()
            logger.error("claude timed out after %ds", CLAUDE_TIMEOUT)
            return ClaudeResult(text="Timed out (5 min limit).", is_error=True)
        except Exception as e:
            logger.exception("Claude runner error")
            return ClaudeResult(text=f"Error: {e}", is_error=True)

    def _parse_output(self, raw: str) -> ClaudeResult:
        try:
            data = json.loads(raw)
            text = data.get("result", raw)
            session_id = data.get("session_id")
            cost = data.get("cost_usd", 0.0)
            duration = data.get("duration_ms", 0.0) / 1000
            return ClaudeResult(
                text=text,
                cost=cost,
                duration=duration,
                session_id=session_id,
            )
        except (json.JSONDecodeError, KeyError):
            # Fallback: treat entire output as text
            return ClaudeResult(text=raw.strip())
