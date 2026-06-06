"""Persistent query history and audit trail."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_PATH = PROJECT_ROOT / "database" / "query_history.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_raw() -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_raw(entries: list[dict[str, Any]]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(
        json.dumps(entries[-100:], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def add_entry(
    question: str,
    sql: str | None,
    summary: str,
    row_count: int,
    success: bool,
    error: str | None = None,
) -> dict[str, Any]:
    """Append a query to persistent history (keeps last 100 entries)."""
    entry = {
        "id": str(uuid4())[:8],
        "timestamp": _now_iso(),
        "question": question,
        "sql": sql,
        "summary": summary,
        "row_count": row_count,
        "success": success,
        "error": error,
    }
    entries = _load_raw()
    entries.append(entry)
    _save_raw(entries)
    return entry


def get_history(limit: int = 20) -> list[dict[str, Any]]:
    """Return most recent history entries (newest first)."""
    entries = _load_raw()
    return list(reversed(entries[-limit:]))


def clear_history() -> None:
    """Remove all stored query history."""
    if HISTORY_PATH.exists():
        HISTORY_PATH.unlink()


def export_history_csv() -> bytes:
    """Export full query history as CSV bytes."""
    entries = _load_raw()
    df = pd.DataFrame(entries)
    if df.empty:
        df = pd.DataFrame(
            columns=["id", "timestamp", "question", "sql", "summary", "row_count", "success", "error"]
        )
    return df.to_csv(index=False).encode("utf-8")
