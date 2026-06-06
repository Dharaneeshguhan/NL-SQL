"""Tests for persistent query history."""

from __future__ import annotations

import json

import pytest

from utils import history as history_mod
from utils.history import add_entry, clear_history, export_history_csv, get_history


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    path = tmp_path / "query_history.json"
    monkeypatch.setattr(history_mod, "HISTORY_PATH", path)
    yield path


class TestQueryHistory:
    def test_add_and_get(self):
        add_entry("Show sales", "SELECT 1", "Summary", 5, True)
        entries = get_history(limit=5)
        assert len(entries) == 1
        assert entries[0]["question"] == "Show sales"
        assert entries[0]["success"] is True
        assert entries[0]["row_count"] == 5

    def test_failed_entry(self):
        add_entry("Bad query", None, "", 0, False, error="SQL failed")
        entries = get_history()
        assert entries[0]["success"] is False
        assert entries[0]["error"] == "SQL failed"

    def test_clear_history(self, isolated_history):
        add_entry("Q1", "SELECT 1", "Ok", 1, True)
        clear_history()
        assert not isolated_history.exists()
        assert get_history() == []

    def test_export_csv(self):
        add_entry("Q1", "SELECT 1", "Ok", 3, True)
        raw = export_history_csv()
        assert b"question" in raw
        assert b"Q1" in raw

    def test_persists_to_disk(self, isolated_history):
        add_entry("Persist test", "SELECT 1", "Done", 2, True)
        data = json.loads(isolated_history.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["question"] == "Persist test"
