# this_file: tests/test_scanner_discovery.py
"""Mocked tests for plugin discovery in IsolatedPedalboardScanner.

CI runners have no real VST3/AU plugins installed, so these tests fake the
plugin folders and the ``auval`` output instead of touching the host system.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from pedalboard_pluginary.scanner_isolated import IsolatedPedalboardScanner


@pytest.fixture
def scanner(tmp_path: Path) -> IsolatedPedalboardScanner:
    """A scanner whose cache and journal live under a throwaway temp dir."""
    from pedalboard_pluginary.cache.sqlite_backend import SQLiteCacheBackend

    backend = SQLiteCacheBackend(db_path=tmp_path / "plugins.db")
    scanner = IsolatedPedalboardScanner(
        cache_backend=backend, journal_path=tmp_path / "journal.db"
    )
    # Start from a clean ignore list so discovery is deterministic.
    scanner.ignores = set()
    return scanner


def test_vst3_discovery_finds_files(
    scanner: IsolatedPedalboardScanner, tmp_path: Path
) -> None:
    """Every ``*.vst3`` file in a scanned folder becomes a scan task."""
    vst3_dir = tmp_path / "VST3"
    vst3_dir.mkdir()
    (vst3_dir / "Reverb.vst3").touch()
    (vst3_dir / "Delay.vst3").touch()

    with (
        patch.object(scanner, "_get_vst3_folders", return_value=[vst3_dir]),
        patch(
            "pedalboard_pluginary.scanner_isolated.platform.system",
            return_value="Linux",
        ),
    ):
        tasks = scanner._find_plugins_to_scan()

    assert (str(vst3_dir / "Reverb.vst3"), "Reverb", "vst3") in tasks
    assert (str(vst3_dir / "Delay.vst3"), "Delay", "vst3") in tasks


def test_vst3_discovery_respects_ignores(
    scanner: IsolatedPedalboardScanner, tmp_path: Path
) -> None:
    """Plugins named in the ignore set are skipped during discovery."""
    vst3_dir = tmp_path / "VST3"
    vst3_dir.mkdir()
    (vst3_dir / "Broken.vst3").touch()
    scanner.ignores = {"vst3/Broken"}

    with (
        patch.object(scanner, "_get_vst3_folders", return_value=[vst3_dir]),
        patch(
            "pedalboard_pluginary.scanner_isolated.platform.system",
            return_value="Linux",
        ),
    ):
        tasks = scanner._find_plugins_to_scan()

    assert tasks == set()


def test_au_discovery_parses_auval(
    scanner: IsolatedPedalboardScanner, tmp_path: Path
) -> None:
    """AU plugins are parsed from ``auval -l`` output on macOS only."""
    plugin_path = tmp_path / "Great.component"
    aufx_line = f"aufx Rvb1 Acme - Acme: Great Reverb (file://{plugin_path})"

    with (
        patch.object(scanner, "_get_vst3_folders", return_value=[]),
        patch.object(scanner, "_list_aufx_plugins", return_value=[aufx_line]),
        patch(
            "pedalboard_pluginary.scanner_isolated.platform.system",
            return_value="Darwin",
        ),
    ):
        tasks = scanner._find_plugins_to_scan()

    assert any(t[2] == "aufx" and t[1] == "Great Reverb" for t in tasks)
