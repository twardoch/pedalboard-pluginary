#!/usr/bin/env python3
# this_file: src/pedalboard_pluginary/scanner_isolated.py

"""
Isolated, resumable scanner that orchestrates subprocess calls to scan_single.py.
Complete process isolation ensures plugin crashes don't affect the main scanner,
and the journaling system ensures scans can be resumed after a crash.
"""
from __future__ import annotations

import logging
import multiprocessing as mp
import os
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Literal, Optional, Tuple
from urllib.parse import unquote, urlparse

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

from .cache.sqlite_backend import SQLiteCacheBackend
from .data import (
    copy_default_ignores,
    get_cache_path,
    load_ignores,
)
from .serialization import deserialize_plugin_info, serialize_plugin_info
from .utils import ensure_folder

logger = logging.getLogger("IsolatedScanner")
console = Console()

# Journal types
PluginId = str
ScanStatus = Literal["pending", "scanning", "success", "failed", "timeout"]


@dataclass
class JournalEntry:
    """Represents a single entry in the scan journal."""

    plugin_id: PluginId
    status: ScanStatus
    result: dict[str, Any] | None = None
    timestamp: float | None = None


class ScanJournal:
    """
    Manages a SQLite-based journal for resumable, transactional plugin scanning.

    This class provides a crash-proof mechanism to track the progress of a plugin
    scan. Each worker process writes its result directly to the journal file,
    ensuring that no progress is lost if the main process crashes.
    """

    def __init__(self, journal_path: Path):
        self.journal_path = journal_path
        # Ensure directory exists before creating any connections
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        # Use a single connection without thread-local storage
        self._conn = None
        self._create_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Gets the database connection, creating if needed."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.journal_path), check_same_thread=False
            )
            self._conn.row_factory = sqlite3.Row
            # Ensure schema exists for this connection
            self._ensure_schema_for_connection(self._conn)
        return self._conn
    
    def _ensure_schema_for_connection(self, conn):
        """Ensure the schema exists for a given connection."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS journal (
                plugin_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result_json TEXT,
                timestamp REAL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_status ON journal (status)
            """
        )

    def _create_schema(self):
        """Creates the necessary tables and indexes if they don't exist."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS journal (
                    plugin_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    timestamp REAL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status ON journal (status)
                """
            )

    def add_pending(self, plugin_paths: set[PluginId]):
        """
        Adds a list of plugin paths to the journal with 'pending' status,
        ignoring any that already exist.
        """
        conn = self._get_connection()
        conn.executemany(
            "INSERT OR IGNORE INTO journal (plugin_id, status) VALUES (?, 'pending')",
            [(path,) for path in plugin_paths],
        )
        conn.commit()

    def get_pending_plugins(self) -> set[PluginId]:
        """Returns a set of all plugin paths marked as 'pending'."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT plugin_id FROM journal WHERE status = 'pending'")
            return {row["plugin_id"] for row in cursor.fetchall()}

    def update_status(
        self,
        plugin_id: PluginId,
        status: ScanStatus,
        result: dict[str, Any] | None = None,
    ):
        """Updates the status and result of a single plugin in the journal."""
        import time

        result_json = (
            serialize_plugin_info(result) if result and status == "success" else None
        )
        conn = self._get_connection()
        conn.execute(
            """
            UPDATE journal
            SET status = ?, result_json = ?, timestamp = ?
            WHERE plugin_id = ?
            """,
            (status, result_json, time.time(), plugin_id),
        )
        conn.commit()

    def get_all_successful(self) -> list[JournalEntry]:
        """Retrieves all successful scan entries from the journal."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM journal WHERE status = 'success' AND result_json IS NOT NULL"
            )
            entries = []
            for row in cursor.fetchall():
                entries.append(
                    JournalEntry(
                        plugin_id=row["plugin_id"],
                        status="success",
                        result=deserialize_plugin_info(row["result_json"]),
                        timestamp=row["timestamp"],
                    )
                )
            return entries

    def get_summary(self) -> dict[ScanStatus, int]:
        """Returns a summary of plugin counts for each status."""
        summary: dict[ScanStatus, int] = {
            "pending": 0,
            "scanning": 0,
            "success": 0,
            "failed": 0,
            "timeout": 0,
        }
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT status, COUNT(*) as count FROM journal GROUP BY status"
            )
            for row in cursor.fetchall():
                if row["status"] in summary:
                    summary[row["status"]] = row["count"]
        return summary

    def delete_journal(self):
        """Deletes the journal file."""
        if self.journal_path.exists():
            self.journal_path.unlink()

    def close(self):
        """Closes the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

def run_scan_single(
    plugin_path: str,
    plugin_name: str,
    plugin_type: str,
    journal_path: str,
    timeout: int,
    verbose: bool,
) -> None:
    """Wrapper to run scan_single.py in a subprocess."""
    journal = ScanJournal(Path(journal_path))
    journal.update_status(plugin_path, "scanning")

    try:
        cmd = [
            sys.executable,
            str(Path(__file__).parent / "scan_single.py"),
            "--plugin-path",
            plugin_path,
            "--plugin-name",
            plugin_name,
            "--plugin-type",
            plugin_type,
            "--journal-path",
            journal_path,
        ]

        if verbose:
            logger.debug(f"Executing: {' '.join(cmd)}")

        subprocess.run(
            cmd,
            capture_output=not verbose,
            text=True,
            timeout=timeout,
            check=True,
            env={**os.environ, 'PYTHONWARNINGS': 'ignore'},
        )

    except subprocess.TimeoutExpired:
        journal.update_status(plugin_path, "timeout")
    except (subprocess.CalledProcessError, Exception) as e:
        journal.update_status(plugin_path, "failed", {"error": str(e)})
    finally:
        journal.close()


class IsolatedPedalboardScanner:
    """Scanner with complete process isolation and resumable journaling."""

    RE_AUFX = re.compile(r"aufx\s+(\w+)\s+(\w+)\s+-\s+(.*?):\s+(.*?)\s+\((\d+)\)")

    def __init__(self, max_workers: Optional[int] = None, timeout: int = 30, verbose: bool = False, cache_backend: Optional[Any] = None, journal_path: Optional[Path] = None):
        self.cache_backend = cache_backend or SQLiteCacheBackend(db_path=get_cache_path("plugins.db"))
        self.journal_path = journal_path or get_cache_path("scan_journal.db")
        self.journal = ScanJournal(self.journal_path)
        self.max_workers = max_workers or min(mp.cpu_count(), 8)
        self.timeout = timeout
        self.verbose = verbose
        self.ensure_ignores()

        if self.verbose:
            logger.setLevel(logging.DEBUG)

    def ensure_ignores(self):
        self.ignores_path = get_cache_path("ignores.json")
        if not self.ignores_path.exists():
            copy_default_ignores(self.ignores_path)
        self.ignores = load_ignores(self.ignores_path)

    def _list_aufx_plugins(self) -> List[str]:
        try:
            result = subprocess.run(
                ["auval", "-l"], capture_output=True, text=True, check=True
            )
            return result.stdout.splitlines()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def _find_plugins_to_scan(
        self,
        extra_folders: Optional[List[str]] = None,
    ) -> set[tuple[str, str, str]]:
        """Find all VST3 and AU plugins and return a set of (path, name, type)."""
        plugin_tasks = set()

        # VST3
        for folder in self._get_vst3_folders(extra_folders):
            for plugin_path in folder.glob("*.vst3"):
                if f"vst3/{plugin_path.stem}" not in self.ignores:
                    # For VST3, we often have multiple plugins in one file.
                    # We will treat the file path as the initial task.
                    plugin_tasks.add((str(plugin_path), plugin_path.stem, "vst3"))

        # AU (macOS only)
        if platform.system() == "Darwin":
            for line in self._list_aufx_plugins():
                match = self.RE_AUFX.match(line)
                if match:
                    _, _, vendor, name, url = match.groups()
                    path = Path(unquote(urlparse(url).path)).resolve()
                    if f"aufx/{path.stem}" not in self.ignores:
                        plugin_tasks.add((str(path), name, "aufx"))

        return plugin_tasks

    def scan(self, extra_folders: Optional[List[str]] = None, rescan: bool = False):
        """Scan all plugins with journaling and process isolation."""
        if rescan:
            console.print("[bold yellow]Clearing cache and starting fresh scan...[/bold yellow]")
            self.cache_backend.clear()
            self.journal.delete_journal()
            # Recreate journal after deletion
            self.journal = ScanJournal(self.journal_path)
            is_resumed_scan = False  # Fresh scan, not a resume
        else:
            is_resumed_scan = self.journal_path.exists()
            if is_resumed_scan:
                console.print("[bold green]Resuming previous scan...[/bold green]")
            else:
                console.print("[bold cyan]Starting new plugin scan...[/bold cyan]")

        # 1. Discover all plugins
        all_plugins = self._find_plugins_to_scan(extra_folders)
        
        # 2. Filter out plugins that already exist in cache (unless rescanning)
        if not rescan:
            try:
                # Get all existing plugin paths from cache (more efficient method)
                existing_plugins = self.cache_backend.get_cached_paths()
                
                # Filter out existing plugins
                new_plugins = {task for task in all_plugins if task[0] not in existing_plugins}
                
                if not new_plugins and not is_resumed_scan:
                    total_cached = len(existing_plugins)
                    console.print(f"[green]All {total_cached} plugins are already cached. Use --rescan to force re-scanning.[/green]")
                    return
                
                # Update all_plugins to only include new ones
                all_plugins = new_plugins
                
                if existing_plugins:
                    console.print(f"[cyan]Found {len(existing_plugins)} cached plugins, scanning {len(all_plugins)} new plugins...[/cyan]")
            except Exception as e:
                logger.debug(f"Could not load existing plugins from cache: {e}")
                # Continue with all plugins if cache check fails
        
        # 3. Add to journal for tracking
        self.journal.add_pending({path for path, _, _ in all_plugins})

        # 4. Get the list of plugins that still need scanning
        plugins_to_scan = self.journal.get_pending_plugins()
        tasks_to_submit = [
            task for task in all_plugins if task[0] in plugins_to_scan
        ]

        if not tasks_to_submit:
            console.print("No new plugins to scan.")
        else:
            # 5. Scan in parallel
            self._execute_scan(tasks_to_submit)

        # 6. Commit results to main cache
        self._commit_journal()

    def _execute_scan(self, tasks: List[Tuple[str, str, str]]):
        """Execute the scan using a ThreadPoolExecutor."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            scan_task = progress.add_task("[cyan]Scanning...", total=len(tasks))

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(
                        run_scan_single,
                        path, name, type, str(self.journal_path), self.timeout, self.verbose
                    ): (path, name)
                    for path, name, type in tasks
                }

                for future in as_completed(futures):
                    path, name = futures[future]
                    try:
                        future.result()  # We don't need the result, just check for exceptions
                    except Exception as e:
                        logger.error(f"Error processing {name}: {e}")
                    progress.update(scan_task, advance=1)

    def _commit_journal(self):
        """Commit successful results from the journal to the main cache."""
        console.print("\n[bold cyan]Finalizing scan and updating cache...[/bold cyan]")
        successful_entries = self.journal.get_all_successful()

        if not successful_entries:
            console.print("[yellow]No new successful scans to commit.[/yellow]")
            self.journal.delete_journal()
            return

        try:
            self.cache_backend.add_plugins(
                [entry.result for entry in successful_entries]
            )
            summary = self.journal.get_summary()
            console.print(
                f"[bold green]Scan complete![/bold green] "
                f"Successful: {summary.get('success', 0)}, "
                f"Failed: {summary.get('failed', 0)}, "
                f"Timed Out: {summary.get('timeout', 0)}"
            )

            # On success, delete the journal
            self.journal.delete_journal()

        except Exception as e:
            console.print(f"[bold red]Error committing to cache: {e}[/bold red]")
            console.print("Journal file has been kept for inspection.")

    def _get_vst3_folders(self, extra_folders=None) -> List[Path]:
        os_name = platform.system()
        folders = []
        if os_name == "Windows":
            folders.extend([
                Path(os.getenv("ProgramFiles", "") + r"\Common Files\VST3"),
                Path(os.getenv("ProgramFiles(x86)", "") + r"\Common Files\VST3"),
            ])
        elif os_name == "Darwin":
            folders.extend([
                Path("~/Library/Audio/Plug-Ins/VST3").expanduser(),
                Path("/Library/Audio/Plug-Ins/VST3"),
            ])
        elif os_name == "Linux":
            folders.extend([
                Path("~/.vst3").expanduser(),
                Path("/usr/lib/vst3"),
                Path("/usr/local/lib/vst3"),
            ])
        if extra_folders:
            folders.extend(Path(p) for p in extra_folders)
        return [folder for folder in folders if folder.exists()]
