"""A file-backed long-term MemoryService (SQLite).

ADK's `InMemoryMemoryService` forgets everything on restart. This implementation
persists each completed session's text to a local SQLite file so **future
campaigns can retrieve prior ones** — no cloud dependency, which suits the
DeepSeek-first stack.

Scope: implements the two methods the harness relies on —
`add_session_to_memory` (ingest a finished session) and `search_memory`
(keyword retrieval). The optional `add_memory` / `add_events_to_memory` hooks are
left to the base class.

Search is deliberately simple keyword matching (SQLite LIKE over whitespace
tokens). It is good enough for "find prior work on X"; swap in FTS5 or a vector
store later behind the same interface without touching callers.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from google.adk.memory import BaseMemoryService
from google.adk.memory.base_memory_service import SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.sessions import Session
from google.genai import types


def _session_text(session: Session) -> str:
    """Flatten a session's event texts into one searchable blob."""
    chunks: list[str] = []
    for event in session.events or []:
        content = getattr(event, "content", None)
        for part in getattr(content, "parts", []) or []:
            if getattr(part, "text", None):
                chunks.append(part.text)
    return "\n".join(chunks).strip()


class FileBackedMemoryService(BaseMemoryService):
    """SQLite-backed memory keyed by (app_name, user_id), searchable by keyword."""

    def __init__(self, db_path: Path) -> None:
        """Open (and initialize) the SQLite store at `db_path`.

        Args:
            db_path: File location; parent dirs are created if missing.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        """Create the memories table on first use (idempotent)."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    author TEXT,
                    timestamp TEXT,
                    text TEXT NOT NULL
                )
                """
            )

    async def add_session_to_memory(self, session: Session) -> None:
        """Persist a finished session's text for later retrieval.

        Args:
            session: The completed ADK session (its events are flattened to text).
        """
        text = _session_text(session)
        if not text:
            return
        ts = str(getattr(session, "last_update_time", "") or "")
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO memories (app_name, user_id, session_id, author, timestamp, text)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (session.app_name, session.user_id, session.id, "session", ts, text),
            )

    async def search_memory(self, *, app_name: str, user_id: str, query: str) -> SearchMemoryResponse:
        """Return prior memories matching `query` (keyword AND over tokens).

        Args:
            app_name: Scope to this app.
            user_id: Scope to this user.
            query: Free-text query; whitespace tokens are matched case-insensitively.

        Returns:
            A `SearchMemoryResponse` whose `memories` are the matching entries
            (most recent first), each as a `MemoryEntry`.
        """
        tokens = [t for t in query.split() if t]
        sql = "SELECT session_id, author, timestamp, text FROM memories WHERE app_name=? AND user_id=?"
        params: list[object] = [app_name, user_id]
        for tok in tokens:
            sql += " AND text LIKE ?"
            params.append(f"%{tok}%")
        sql += " ORDER BY id DESC LIMIT 20"
        with self._lock, self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        memories = [
            MemoryEntry(
                content=types.Content(role="model", parts=[types.Part(text=text)]),
                author=author or "session",
                timestamp=timestamp or None,
            )
            for (_sid, author, timestamp, text) in rows
        ]
        return SearchMemoryResponse(memories=memories)
