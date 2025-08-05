#!/usr/bin/env python3
# this_file: src/pedalboard_pluginary/scanner_parallel.py

"""Parallel scanner with process isolation for stability."""

import json
import logging
import multiprocessing as mp
import os
import platform
import re
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

import pedalboard
from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table

from .data import (
    copy_default_ignores,
    get_cache_path,
    load_ignores,
    load_json_file,
    save_json_file,
)
from .utils import ensure_folder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ParallelScanner")
console = Console()


def scan_plugin_subprocess(plugin_path: str, plugin_name: str, plugin_type: str) -> dict:
    """Scan a plugin in a subprocess for isolation."""
    try:
        # Run scanner_worker as a subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pedalboard_pluginary.scanner_worker", 
             plugin_path, plugin_name, plugin_type],
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout per plugin
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {
                "name": plugin_name,
                "path": plugin_path,
                "type": plugin_type,
                "success": False,
                "error": f"Worker process failed: {result.stderr}"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "name": plugin_name,
            "path": plugin_path,
            "type": plugin_type,
            "success": False,
            "error": "Plugin scan timed out after 30 seconds"
        }
    except Exception as e:
        return {
            "name": plugin_name,
            "path": plugin_path,
            "type": plugin_type,
            "success": False,
            "error": str(e)
        }


class ParallelPedalboardScanner:
    """Scanner with parallel processing and process isolation."""
    
    RE_AUFX = re.compile(r"aufx\s+(\w+)\s+(\w+)\s+-\s+(.*?):\s+(.*?)\s+\((.*?)\)")
    
    def __init__(self, max_workers: Optional[int] = None):
        self.plugins_path = get_cache_path("plugins")
        self.plugins = {}
        self.failed_plugins = {}
        self.safe_save = True
        self.max_workers = max_workers or min(mp.cpu_count(), 8)
        self.ensure_ignores()
        
    def ensure_ignores(self):
        self.ignores_path = get_cache_path("ignores")
        if self.ignores_path.is_dir():
            logger.warning(f"'{self.ignores_path}' is a directory, removing it.")
            shutil.rmtree(self.ignores_path)
        if not self.ignores_path.exists():
            copy_default_ignores(self.ignores_path)
        self.ignores = load_ignores(self.ignores_path)
    
    def save_plugins(self):
        ensure_folder(self.plugins_path)
        save_json_file(dict(sorted(self.plugins.items())), self.plugins_path)
        
        # Also save failed plugins for debugging
        if self.failed_plugins:
            failed_path = get_cache_path("failed_plugins")
            save_json_file(self.failed_plugins, failed_path)
    
    def _list_aufx_plugins(self):
        """List Audio Unit plugins using auval."""
        try:
            result = subprocess.run(
                ["auval", "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=True,
            )
            return result.stdout.splitlines()
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running auval: {e}")
            return []
    
    def _find_aufx_plugins(self) -> List[Tuple[Path, str, str]]:
        """Find AU plugins and return (path, vendor_name, plugin_name) tuples."""
        aufx_plugins = []
        plugin_type = "aufx"
        
        for line in self._list_aufx_plugins():
            match = self.RE_AUFX.match(line)
            if match:
                (plugin_code, vendor_code, vendor_name, 
                 plugin_name, plugin_url) = match.groups()
                
                plugin_path = Path(unquote(urlparse(plugin_url).path)).resolve()
                plugin_fn = plugin_path.stem
                plugin_key = f"{plugin_type}/{plugin_fn}"
                
                if plugin_key not in self.ignores:
                    aufx_plugins.append((plugin_path, vendor_name, plugin_name))
                    
        return aufx_plugins
    
    def _get_vst3_folders(self, extra_folders=None):
        """Get VST3 plugin folders for the current platform."""
        os_name = platform.system()
        
        if os_name == "Windows":
            folders = [
                Path(os.getenv("ProgramFiles", "") + r"\Common Files\VST3"),
                Path(os.getenv("ProgramFiles(x86)", "") + r"\Common Files\VST3"),
            ]
        elif os_name == "Darwin":  # macOS
            folders = [
                Path("~/Library/Audio/Plug-Ins/VST3").expanduser(),
                Path("/Library/Audio/Plug-Ins/VST3"),
            ]
        elif os_name == "Linux":
            folders = [
                Path("~/.vst3").expanduser(),
                Path("/usr/lib/vst3"),
                Path("/usr/local/lib/vst3"),
            ]
        else:
            folders = []
        
        if extra_folders:
            folders.extend(Path(p) for p in extra_folders)
        
        return [folder for folder in folders if folder.exists()]
    
    def _find_vst3_plugins(self, extra_folders=None) -> List[Path]:
        """Find VST3 plugins."""
        vst3_plugins = []
        plugin_type = "vst3"
        
        for folder in self._get_vst3_folders(extra_folders=extra_folders):
            for plugin_path in folder.glob(f"*.{plugin_type}"):
                plugin_fn = plugin_path.stem
                plugin_key = f"{plugin_type}/{plugin_fn}"
                if plugin_key not in self.ignores:
                    vst3_plugins.append(plugin_path)
                    
        return vst3_plugins
    
    def scan_plugins_parallel(self, plugin_tasks: List[Tuple[str, str, str, Optional[str]]]):
        """Scan plugins in parallel with beautiful progress display.
        
        Args:
            plugin_tasks: List of (path, name, type, vendor) tuples
        """
        total_tasks = len(plugin_tasks)
        
        if total_tasks == 0:
            return
        
        # Create progress display with Rich
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
            transient=True
        ) as progress:
            
            main_task = progress.add_task(
                "[cyan]Scanning plugins...", total=total_tasks
            )
            
            # Create a table for current status
            def create_status_table(current_plugin="", vendor="", status=""):
                table = Table(show_header=False, box=None, padding=(0, 2))
                table.add_column(style="cyan", width=50)
                table.add_column(style="yellow", width=30)
                table.add_column(style="green", width=20)
                
                if current_plugin:
                    table.add_row(current_plugin, vendor or "...", status)
                    
                return table
            
            completed = 0
            failed = 0
            
            # Process in parallel
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_task = {}
                for path, name, plugin_type, vendor in plugin_tasks:
                    future = executor.submit(scan_plugin_subprocess, str(path), name, plugin_type)
                    future_to_task[future] = (path, name, plugin_type, vendor)
                
                # Process completed tasks
                for future in as_completed(future_to_task):
                    path, name, plugin_type, vendor = future_to_task[future]
                    plugin_name = Path(path).stem
                    
                    try:
                        result = future.result(timeout=1)
                        
                        if result.get("success", False):
                            # Store successful plugin
                            plugin_entry = {
                                "name": result["name"],
                                "path": result["path"],
                                "filename": result.get("filename", plugin_name),
                                "type": result["type"],
                                "params": result.get("params", {}),
                            }
                            
                            # Add manufacturer if available
                            if result.get("manufacturer"):
                                plugin_entry["manufacturer"] = result["manufacturer"]
                            elif vendor:
                                plugin_entry["manufacturer"] = vendor
                            
                            self.plugins[result["name"]] = plugin_entry
                            completed += 1
                            status = "✓"
                        else:
                            # Store failed plugin info
                            self.failed_plugins[name] = {
                                "path": str(path),
                                "type": plugin_type,
                                "error": result.get("error", "Unknown error")
                            }
                            failed += 1
                            status = "✗"
                            
                    except Exception as e:
                        self.failed_plugins[name] = {
                            "path": str(path),
                            "type": plugin_type,
                            "error": str(e)
                        }
                        failed += 1
                        status = "✗"
                    
                    # Update progress
                    progress.update(
                        main_task, 
                        advance=1,
                        description=f"[cyan]Scanning plugins... [green]{completed} OK [red]{failed} failed"
                    )
                    
                    # Save periodically
                    if self.safe_save and (completed + failed) % 10 == 0:
                        self.save_plugins()
        
        # Final save
        self.save_plugins()
        
        # Report results
        console.print(f"\n[green]✓[/green] Successfully scanned {completed} plugins")
        if failed > 0:
            console.print(f"[red]✗[/red] Failed to scan {failed} plugins")
            console.print(f"   See {get_cache_path('failed_plugins')} for details")
    
    def scan(self, extra_folders=None):
        """Scan all plugins with parallel processing."""
        logger.info("\n>> Scanning plugins with parallel processing...")
        
        # Collect all plugin tasks
        plugin_tasks = []
        
        # VST3 plugins
        for plugin_path in self._find_vst3_plugins(extra_folders=extra_folders):
            try:
                # Get plugin names for this file
                plugin_names = pedalboard.VST3Plugin.get_plugin_names_for_file(str(plugin_path))
                for plugin_name in plugin_names:
                    if plugin_name not in self.plugins:
                        plugin_tasks.append((str(plugin_path), plugin_name, "vst3", None))
            except Exception as e:
                logger.warning(f"Could not get plugin names for {plugin_path}: {e}")
        
        # AU plugins (macOS only)
        if platform.system() == "Darwin":
            for plugin_path, vendor_name, plugin_name in self._find_aufx_plugins():
                try:
                    # Get plugin names for this file
                    plugin_names = pedalboard.AudioUnitPlugin.get_plugin_names_for_file(str(plugin_path))
                    for name in plugin_names:
                        if name not in self.plugins:
                            plugin_tasks.append((str(plugin_path), name, "aufx", vendor_name))
                except Exception as e:
                    logger.warning(f"Could not get plugin names for {plugin_path}: {e}")
        
        # Scan in parallel
        self.scan_plugins_parallel(plugin_tasks)
        
        logger.info("\n>> Done!")
    
    def rescan(self, extra_folders=None):
        """Clear cache and rescan all plugins."""
        self.plugins = {}
        self.failed_plugins = {}
        self.scan(extra_folders=extra_folders)
    
    def update(self, extra_folders=None):
        """Update with only new plugins."""
        logger.info("\n>> Scanning for new plugins...")
        
        if not self.plugins_path.exists():
            self.rescan(extra_folders=extra_folders)
            return
        
        self.plugins = load_json_file(self.plugins_path)
        
        # Collect new plugin tasks
        plugin_tasks = []
        
        # Check for new VST3 plugins
        existing_vst3 = {
            Path(p["path"]).resolve()
            for p in self.plugins.values()
            if p["type"] == "vst3"
        }
        
        for plugin_path in self._find_vst3_plugins(extra_folders=extra_folders):
            if plugin_path.resolve() not in existing_vst3:
                try:
                    plugin_names = pedalboard.VST3Plugin.get_plugin_names_for_file(str(plugin_path))
                    for plugin_name in plugin_names:
                        if plugin_name not in self.plugins:
                            plugin_tasks.append((str(plugin_path), plugin_name, "vst3", None))
                except Exception as e:
                    logger.warning(f"Could not get plugin names for {plugin_path}: {e}")
        
        # Check for new AU plugins
        if platform.system() == "Darwin":
            existing_aufx = {
                Path(p["path"]).resolve()
                for p in self.plugins.values()
                if p["type"] == "aufx"
            }
            
            for plugin_path, vendor_name, plugin_name in self._find_aufx_plugins():
                if plugin_path.resolve() not in existing_aufx:
                    try:
                        plugin_names = pedalboard.AudioUnitPlugin.get_plugin_names_for_file(str(plugin_path))
                        for name in plugin_names:
                            if name not in self.plugins:
                                plugin_tasks.append((str(plugin_path), name, "aufx", vendor_name))
                    except Exception as e:
                        logger.warning(f"Could not get plugin names for {plugin_path}: {e}")
        
        if plugin_tasks:
            self.scan_plugins_parallel(plugin_tasks)
        else:
            logger.info("No new plugins found.")
        
        logger.info("\n>> Done!")