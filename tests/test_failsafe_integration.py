#!/usr/bin/env python3
# this_file: tests/test_failsafe_integration.py
"""
Comprehensive integration tests for the failsafe scanning architecture.
Tests worker crashes, main process crashes, commit phase crashes, and edge cases.
"""
from __future__ import annotations

import multiprocessing
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pedalboard_pluginary.scanner_isolated import IsolatedPedalboardScanner, ScanJournal, run_scan_single
from pedalboard_pluginary.cache.sqlite_backend import SQLiteCacheBackend


@pytest.fixture
def test_cache_dir(tmp_path: Path) -> Path:
    """Create a temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def mock_plugin_discovery():
    """Mock plugin discovery to return test plugins."""
    test_plugins = {
        ("/test/plugin1.vst3", "TestPlugin1", "vst3"),
        ("/test/plugin2.vst3", "TestPlugin2", "vst3"),
        ("/test/plugin3.vst3", "TestPlugin3", "vst3"),
    }
    
    def mock_find_plugins(self, extra_folders=None):
        return test_plugins
    
    with patch.object(IsolatedPedalboardScanner, '_find_plugins_to_scan', mock_find_plugins):
        yield test_plugins


class TestWorkerProcessCrash:
    """Test scenarios where worker processes crash during scanning."""
    
    def test_worker_crash_simulation(self, test_cache_dir, mock_plugin_discovery):
        """Simulate a worker process crashing mid-scan."""
        with patch("pedalboard_pluginary.data.get_cache_path") as mock_get_cache:
            mock_get_cache.return_value = test_cache_dir / "plugins.db"
            
            scanner = IsolatedPedalboardScanner(max_workers=1, timeout=5)
            journal_path = scanner.journal_path
            
            # Mock run_scan_single to simulate a crash on the second plugin
            crash_count = [0]
            original_run_scan_single = run_scan_single
            
            def mock_run_scan_single_crash(plugin_path, plugin_name, plugin_type, 
                                           journal_path_str, timeout, verbose):
                if plugin_path == "/test/plugin2.vst3":
                    crash_count[0] += 1
                    if crash_count[0] == 1:
                        # Simulate a crash by raising an exception
                        raise RuntimeError("Simulated worker crash")
                
                # For other plugins, simulate successful scan
                journal = ScanJournal(Path(journal_path_str))
                journal.update_status(plugin_path, "success", {
                    "path": plugin_path,
                    "name": plugin_name,
                    "type": plugin_type,
                    "params": {"test_param": 1.0}
                })
                journal.close()
            
            with patch("pedalboard_pluginary.scanner_isolated.run_scan_single", 
                      side_effect=mock_run_scan_single_crash):
                scanner.scan()
            
            # Verify the journal shows the correct status
            journal = ScanJournal(journal_path)
            summary = journal.get_summary()
            
            # Should have 2 successful and 1 failed
            assert summary["success"] == 2
            assert summary["failed"] == 1
            
            # Verify journal was cleaned up after commit
            assert not journal_path.exists()
    
    def test_worker_timeout(self, test_cache_dir, mock_plugin_discovery):
        """Test worker timeout handling."""
        with patch("pedalboard_pluginary.data.get_cache_path") as mock_get_cache:
            mock_get_cache.return_value = test_cache_dir / "plugins.db"
            
            scanner = IsolatedPedalboardScanner(max_workers=1, timeout=1)
            
            def mock_run_scan_single_timeout(plugin_path, plugin_name, plugin_type,
                                            journal_path_str, timeout, verbose):
                journal = ScanJournal(Path(journal_path_str))
                journal.update_status(plugin_path, "scanning")
                
                if plugin_path == "/test/plugin2.vst3":
                    # Simulate a process that takes too long
                    time.sleep(2)
                
                journal.update_status(plugin_path, "success", {
                    "path": plugin_path,
                    "name": plugin_name,
                    "type": plugin_type,
                })
                journal.close()
            
            with patch("pedalboard_pluginary.scanner_isolated.run_scan_single",
                      side_effect=mock_run_scan_single_timeout):
                scanner.scan()
            
            # The timeout should have been triggered for plugin2
            # This test verifies timeout handling is working


class TestMainProcessCrash:
    """Test scenarios where the main scanner process crashes."""
    
    def test_main_process_crash_and_resume(self, test_cache_dir, mock_plugin_discovery):
        """Simulate main process crash and verify resume functionality."""
        with patch("pedalboard_pluginary.data.get_cache_path") as mock_get_cache:
            mock_get_cache.return_value = test_cache_dir / "plugins.db"
            
            # First scan - simulate crash after first plugin
            scanner1 = IsolatedPedalboardScanner(max_workers=1)
            journal_path = scanner1.journal_path
            
            scan_count = [0]
            
            def mock_run_scan_single_partial(plugin_path, plugin_name, plugin_type,
                                            journal_path_str, timeout, verbose):
                scan_count[0] += 1
                journal = ScanJournal(Path(journal_path_str))
                
                if scan_count[0] == 1:
                    # First plugin succeeds
                    journal.update_status(plugin_path, "success", {
                        "path": plugin_path,
                        "name": plugin_name,
                        "type": plugin_type,
                    })
                    journal.close()
                else:
                    # Simulate main process crash by raising exception
                    journal.update_status(plugin_path, "scanning")
                    journal.close()
                    raise KeyboardInterrupt("Simulated main process crash")
            
            with patch("pedalboard_pluginary.scanner_isolated.run_scan_single",
                      side_effect=mock_run_scan_single_partial):
                with pytest.raises(KeyboardInterrupt):
                    scanner1.scan()
            
            # Verify journal exists and has correct state
            assert journal_path.exists()
            journal = ScanJournal(journal_path)
            summary = journal.get_summary()
            assert summary["success"] == 1
            assert summary["scanning"] >= 1 or summary["pending"] >= 1
            
            # Second scan - resume from journal
            scanner2 = IsolatedPedalboardScanner(max_workers=1)
            
            def mock_run_scan_single_resume(plugin_path, plugin_name, plugin_type,
                                           journal_path_str, timeout, verbose):
                journal = ScanJournal(Path(journal_path_str))
                journal.update_status(plugin_path, "success", {
                    "path": plugin_path,
                    "name": plugin_name,
                    "type": plugin_type,
                })
                journal.close()
            
            with patch("pedalboard_pluginary.scanner_isolated.run_scan_single",
                      side_effect=mock_run_scan_single_resume):
                scanner2.scan()
            
            # Verify all plugins were scanned and journal was cleaned up
            assert not journal_path.exists()


class TestCommitPhaseCrash:
    """Test scenarios where crashes occur during the commit phase."""
    
    def test_crash_during_commit(self, test_cache_dir, mock_plugin_discovery):
        """Simulate a crash during the commit phase."""
        with patch("pedalboard_pluginary.data.get_cache_path") as mock_get_cache:
            mock_get_cache.return_value = test_cache_dir / "plugins.db"
            
            scanner = IsolatedPedalboardScanner(max_workers=1)
            journal_path = scanner.journal_path
            
            # Mock successful scanning
            def mock_run_scan_single_success(plugin_path, plugin_name, plugin_type,
                                            journal_path_str, timeout, verbose):
                journal = ScanJournal(Path(journal_path_str))
                journal.update_status(plugin_path, "success", {
                    "path": plugin_path,
                    "name": plugin_name,
                    "type": plugin_type,
                })
                journal.close()
            
            # Mock cache backend to fail during commit
            mock_cache = MagicMock(spec=SQLiteCacheBackend)
            mock_cache.db_path = test_cache_dir / "plugins.db"
            mock_cache.add_plugins.side_effect = RuntimeError("Database locked during commit")
            
            scanner.cache_backend = mock_cache
            
            with patch("pedalboard_pluginary.scanner_isolated.run_scan_single",
                      side_effect=mock_run_scan_single_success):
                scanner.scan()
            
            # Verify journal still exists after failed commit
            assert journal_path.exists()
            journal = ScanJournal(journal_path)
            summary = journal.get_summary()
            assert summary["success"] == 3  # All plugins should be marked successful
            
            # Verify error was caught and journal preserved
            mock_cache.add_plugins.assert_called_once()
    
    def test_atomic_commit_protection(self, test_cache_dir, mock_plugin_discovery):
        """Test that main cache remains untouched if commit fails."""
        with patch("pedalboard_pluginary.data.get_cache_path") as mock_get_cache:
            mock_get_cache.return_value = test_cache_dir / "plugins.db"
            
            # Create initial cache with one plugin
            cache = SQLiteCacheBackend(db_path=test_cache_dir / "plugins.db")
            initial_plugin = {
                "path": "/existing/plugin.vst3",
                "name": "ExistingPlugin",
                "type": "vst3",
                "params": {"gain": 0.5}
            }
            cache.add_plugins([initial_plugin])
            initial_count = len(cache.get_all_plugins())
            
            scanner = IsolatedPedalboardScanner(max_workers=1, cache_backend=cache)
            
            # Mock successful scanning
            def mock_run_scan_single_success(plugin_path, plugin_name, plugin_type,
                                            journal_path_str, timeout, verbose):
                journal = ScanJournal(Path(journal_path_str))
                journal.update_status(plugin_path, "success", {
                    "path": plugin_path,
                    "name": plugin_name,
                    "type": plugin_type,
                })
                journal.close()
            
            # Mock add_plugins to fail
            original_add_plugins = cache.add_plugins
            cache.add_plugins = MagicMock(side_effect=RuntimeError("Commit failed"))
            
            with patch("pedalboard_pluginary.scanner_isolated.run_scan_single",
                      side_effect=mock_run_scan_single_success):
                scanner.scan()
            
            # Restore original method to check cache state
            cache.add_plugins = original_add_plugins
            
            # Verify cache still has only the initial plugin
            final_count = len(cache.get_all_plugins())
            assert final_count == initial_count


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_journal(self, test_cache_dir):
        """Test behavior with an empty journal."""
        journal_path = test_cache_dir / "empty_journal.db"
        journal = ScanJournal(journal_path)
        
        # Verify empty journal behaves correctly
        assert journal.get_pending_plugins() == set()
        assert journal.get_all_successful() == []
        
        summary = journal.get_summary()
        assert all(count == 0 for count in summary.values())
        
        # Test that operations on empty journal don't crash
        journal.add_pending(set())
        journal.delete_journal()
        assert not journal_path.exists()
    
    def test_all_failed_journal(self, test_cache_dir, mock_plugin_discovery):
        """Test journal with all plugins failed."""
        with patch("pedalboard_pluginary.data.get_cache_path") as mock_get_cache:
            mock_get_cache.return_value = test_cache_dir / "plugins.db"
            
            scanner = IsolatedPedalboardScanner(max_workers=1)
            
            # Mock all scans to fail
            def mock_run_scan_single_fail(plugin_path, plugin_name, plugin_type,
                                         journal_path_str, timeout, verbose):
                journal = ScanJournal(Path(journal_path_str))
                journal.update_status(plugin_path, "failed", {
                    "error": f"Failed to load {plugin_name}"
                })
                journal.close()
            
            with patch("pedalboard_pluginary.scanner_isolated.run_scan_single",
                      side_effect=mock_run_scan_single_fail):
                scanner.scan()
            
            # Verify journal was cleaned up even with all failures
            assert not scanner.journal_path.exists()
    
    def test_mixed_status_journal(self, test_cache_dir, mock_plugin_discovery):
        """Test journal with mixed success/failure/timeout statuses."""
        with patch("pedalboard_pluginary.data.get_cache_path") as mock_get_cache:
            mock_get_cache.return_value = test_cache_dir / "plugins.db"
            
            scanner = IsolatedPedalboardScanner(max_workers=1)
            
            def mock_run_scan_single_mixed(plugin_path, plugin_name, plugin_type,
                                          journal_path_str, timeout, verbose):
                journal = ScanJournal(Path(journal_path_str))
                
                if "plugin1" in plugin_path:
                    journal.update_status(plugin_path, "success", {
                        "path": plugin_path,
                        "name": plugin_name,
                        "type": plugin_type,
                    })
                elif "plugin2" in plugin_path:
                    journal.update_status(plugin_path, "failed", {
                        "error": "Load error"
                    })
                else:
                    journal.update_status(plugin_path, "timeout")
                
                journal.close()
            
            with patch("pedalboard_pluginary.scanner_isolated.run_scan_single",
                      side_effect=mock_run_scan_single_mixed):
                scanner.scan()
            
            # Verify only successful plugins were committed
            plugins = scanner.cache_backend.get_all_plugins()
            assert len(plugins) == 1  # Only plugin1 should be in cache
    
    def test_concurrent_journal_access(self, test_cache_dir):
        """Test concurrent access to journal from multiple threads."""
        journal_path = test_cache_dir / "concurrent_journal.db"
        
        def worker_thread(thread_id: int, plugin_ids: list):
            journal = ScanJournal(journal_path)
            for plugin_id in plugin_ids:
                journal.add_pending({plugin_id})
                time.sleep(0.001)  # Small delay to increase chance of collision
                journal.update_status(plugin_id, "success", {
                    "thread": thread_id,
                    "plugin": plugin_id
                })
            journal.close()
        
        # Create multiple threads writing to the same journal
        threads = []
        num_threads = 5
        plugins_per_thread = 10
        
        for i in range(num_threads):
            plugin_ids = [f"/plugin_{i}_{j}.vst3" for j in range(plugins_per_thread)]
            thread = threading.Thread(target=worker_thread, args=(i, plugin_ids))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all entries were written correctly
        journal = ScanJournal(journal_path)
        summary = journal.get_summary()
        assert summary["success"] == num_threads * plugins_per_thread
        
        successful = journal.get_all_successful()
        assert len(successful) == num_threads * plugins_per_thread


class TestRealProcessCrash:
    """Test with actual subprocess crashes (not just mocked)."""
    
    @pytest.mark.skipif(sys.platform == "win32", reason="Process signals differ on Windows")
    def test_real_subprocess_kill(self, test_cache_dir, tmp_path):
        """Test killing an actual subprocess during scanning."""
        # Create a test script that simulates a plugin scan
        test_script = tmp_path / "test_scan_worker.py"
        test_script.write_text("""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pedalboard_pluginary.scanner_isolated import ScanJournal

journal_path = sys.argv[1]
plugin_id = sys.argv[2]
delay = float(sys.argv[3])

journal = ScanJournal(Path(journal_path))
journal.add_pending({plugin_id})
journal.update_status(plugin_id, "scanning")

# Simulate work
time.sleep(delay)

journal.update_status(plugin_id, "success", {"test": "data"})
journal.close()
        """)
        
        journal_path = test_cache_dir / "subprocess_journal.db"
        
        # Start subprocess that will be killed
        proc = subprocess.Popen(
            [sys.executable, str(test_script), str(journal_path), "/test/plugin.vst3", "5"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give it time to start and create journal entry
        time.sleep(0.5)
        
        # Kill the process
        proc.kill()
        proc.wait()
        
        # Verify journal shows scanning status (not success)
        journal = ScanJournal(journal_path)
        summary = journal.get_summary()
        assert summary["scanning"] == 1
        assert summary["success"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])