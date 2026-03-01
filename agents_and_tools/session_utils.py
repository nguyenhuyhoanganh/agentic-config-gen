"""Session and context optimization: limit history, optional summarization (RAG-like for messages)."""

from __future__ import annotations

from pathlib import Path

from agents import RunConfig, SessionSettings, SQLiteSession

# Project root
_BASE = Path(__file__).resolve().parent.parent
_DB_DIR = _BASE / "session_data"


def get_session_db_path(conversation_id: str) -> Path:
    """SQLite file per conversation. Create dir if needed."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    # Safe filename
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in conversation_id)
    return _DB_DIR / f"{safe_id}.db"


def create_session(conversation_id: str) -> SQLiteSession:
    """Create a SQLiteSession for this conversation_id."""
    path = get_session_db_path(conversation_id)
    return SQLiteSession(conversation_id, str(path))


def run_config_with_context_limit(limit: int = 50):
    """RunConfig that caps session history to last `limit` items (optimize context length)."""
    return RunConfig(session_settings=SessionSettings(limit=limit))
