"""SQLite session persistence."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "sessions.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            user_id INTEGER PRIMARY KEY,
            project_dir TEXT,
            session_id TEXT,
            model TEXT,
            permission_mode TEXT DEFAULT 'bypassPermissions',
            total_cost REAL DEFAULT 0,
            total_duration REAL DEFAULT 0,
            message_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def load_session(user_id: int) -> dict | None:
    conn = _connect()
    row = conn.execute(
        "SELECT project_dir, session_id, model, permission_mode, "
        "total_cost, total_duration, message_count FROM sessions WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "project_dir": row[0],
        "session_id": row[1],
        "model": row[2],
        "permission_mode": row[3] or "bypassPermissions",
        "total_cost": row[4] or 0.0,
        "total_duration": row[5] or 0.0,
        "message_count": row[6] or 0,
    }


def save_session(user_id: int, session) -> None:
    conn = _connect()
    conn.execute(
        "INSERT OR REPLACE INTO sessions "
        "(user_id, project_dir, session_id, model, permission_mode, "
        "total_cost, total_duration, message_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
            str(session.project_dir) if session.project_dir else None,
            session.session_id,
            session.model,
            session.permission_mode,
            session.total_cost,
            session.total_duration,
            session.message_count,
        ),
    )
    conn.commit()
    conn.close()


def delete_session(user_id: int) -> None:
    conn = _connect()
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
