import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from pedalboard_pluginary.cache.sqlite_backend import SQLiteCacheBackend
from pedalboard_pluginary.scanner_isolated import IsolatedPedalboardScanner, ScanJournal


def _valid_result(path: str, name: str, plugin_type: str) -> dict:
    """Build a serialized-plugin dict the cache backend will accept."""
    return {
        "id": f"{plugin_type}/{name}",
        "name": name,
        "path": path,
        "filename": f"{name}.{plugin_type}",
        "plugin_type": plugin_type,
        "parameters": {},
    }


@pytest.fixture
def journal_path(tmp_path: Path) -> Path:
    return tmp_path / "test_journal.db"


@pytest.fixture
def journal(journal_path: Path) -> ScanJournal:
    return ScanJournal(journal_path)


def test_journal_creation(journal: ScanJournal, journal_path: Path):
    assert journal_path.exists()
    with sqlite3.connect(journal_path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='journal'"
        )
        assert cursor.fetchone() is not None


def test_add_and_get_pending(journal: ScanJournal):
    plugins = {"/path/to/plugin1", "/path/to/plugin2"}
    journal.add_pending(plugins)
    pending = journal.get_pending_plugins()
    assert pending == plugins


def test_update_status(journal: ScanJournal):
    plugin_id = "/path/to/plugin1"
    journal.add_pending({plugin_id})
    journal.update_status(plugin_id, "success", {"foo": "bar"})

    with sqlite3.connect(journal.journal_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT status, result_json FROM journal WHERE plugin_id=?", (plugin_id,)
        )
        row = cursor.fetchone()
        assert row["status"] == "success"
        assert row["result_json"] is not None


def test_get_summary(journal: ScanJournal):
    journal.add_pending({"/path/to/plugin1", "/path/to/plugin2", "/path/to/plugin3"})
    journal.update_status("/path/to/plugin1", "success")
    journal.update_status("/path/to/plugin2", "failed")
    summary = journal.get_summary()
    assert summary["success"] == 1
    assert summary["failed"] == 1
    assert summary["pending"] == 1


@patch("pedalboard_pluginary.scanner_isolated.run_scan_single")
def test_scan_resume(mock_run_scan_single, tmp_path: Path):
    """A pre-existing journal resumes scanning only the still-pending plugins."""
    journal_path = tmp_path / "scan_journal.db"
    cache = SQLiteCacheBackend(db_path=tmp_path / "plugins.db")

    plugin1 = ("/path/to/plugin1", "Plugin1", "vst3")
    plugin2 = ("/path/to/plugin2", "Plugin2", "vst3")

    # Seed a journal as if a previous scan finished plugin1 then was killed
    # before it could reach plugin2 or commit.
    seed = ScanJournal(journal_path)
    seed.add_pending({plugin1[0], plugin2[0]})
    seed.update_status(plugin1[0], "success", _valid_result(*plugin1))
    seed.close()

    def mark_success(path, name, plugin_type, journal_path_str, timeout, verbose):
        journal = ScanJournal(Path(journal_path_str))
        journal.update_status(path, "success", _valid_result(path, name, plugin_type))
        journal.close()

    mock_run_scan_single.side_effect = mark_success

    scanner = IsolatedPedalboardScanner(cache_backend=cache, journal_path=journal_path)
    with patch.object(
        IsolatedPedalboardScanner,
        "_find_plugins_to_scan",
        return_value={plugin1, plugin2},
    ):
        scanner.scan()

    # Only the still-pending plugin2 should have been scanned on resume.
    mock_run_scan_single.assert_called_once_with(
        plugin2[0],
        plugin2[1],
        plugin2[2],
        str(journal_path),
        scanner.timeout,
        scanner.verbose,
    )

    # Both plugins end up committed and the journal is cleaned up on success.
    assert not journal_path.exists()
    committed = {p["path"] for p in cache.get_all_plugins()}
    assert committed == {plugin1[0], plugin2[0]}
