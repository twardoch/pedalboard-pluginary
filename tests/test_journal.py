import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pedalboard_pluginary.scanner_isolated import IsolatedPedalboardScanner, ScanJournal


@pytest.fixture
def journal_path(tmp_path: Path) -> Path:
    return tmp_path / "test_journal.db"


@pytest.fixture
def journal(journal_path: Path) -> ScanJournal:
    return ScanJournal(journal_path)


def test_journal_creation(journal: ScanJournal, journal_path: Path):
    assert journal_path.exists()
    with sqlite3.connect(journal_path) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='journal'")
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
        cursor = conn.execute("SELECT status, result_json FROM journal WHERE plugin_id=?", (plugin_id,))
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
    """Simulate a crash and resume a scan."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    mock_cache_backend = MagicMock()
    with patch("pedalboard_pluginary.data.get_cache_path", return_value=cache_dir / "plugins.db"):
        # 1. Initial scan that "crashes"
        scanner1 = IsolatedPedalboardScanner(cache_backend=mock_cache_backend)
        plugins_to_scan = {
            ("/path/to/plugin1", "Plugin 1", "vst3"),
            ("/path/to/plugin2", "Plugin 2", "vst3"),
        }

        # Simulate that scan_single is called only for the first plugin
        def side_effect_crash(*args, **kwargs):
            if kwargs["plugin_path"] == "/path/to/plugin1":
                # Simulate a successful scan for plugin1
                journal = ScanJournal(Path(kwargs["journal_path"]))
                journal.update_status(kwargs["plugin_path"], "success", {"name": "Plugin 1"})
                journal.close()
            else:
                # Simulate a crash before the second plugin is scanned
                raise Exception("Simulated crash")

        mock_run_scan_single.side_effect = side_effect_crash

        with pytest.raises(Exception, match="Simulated crash"):
            scanner1.scan(rescan=True)

        # Verify that the journal file exists and has the correct state
        assert scanner1.journal_path.exists()
        summary1 = scanner1.journal.get_summary()
        assert summary1["success"] == 1
        assert summary1["pending"] == 1

        # 2. Resumed scan
        mock_run_scan_single.side_effect = None  # Reset side effect
        scanner2 = IsolatedPedalboardScanner()
        scanner2.scan()

        # Verify that scan_single was only called for the pending plugin
        mock_run_scan_single.assert_called_once_with(
            "/path/to/plugin2",
            "Plugin 2",
            "vst3",
            str(scanner2.journal_path),
            scanner2.timeout,
            scanner2.verbose,
        )

        # Verify that the journal is deleted after a successful commit
        assert not scanner2.journal_path.exists()
