#!/usr/bin/env python3
# this_file: src/pedalboard_pluginary/scanner_isolated.py

"""
Isolated scanner that orchestrates subprocess calls to scan_single.py.
Complete process isolation ensures plugin crashes don't affect the main scanner.
"""

import json
import logging
import multiprocessing as mp
import os
import platform
import re
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

import pedalboard
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from rich.table import Table

from .data import (
    copy_default_ignores,
    get_cache_path,
    load_ignores,
    load_json_file,
    save_json_file,
)
from .utils import ensure_folder

logger = logging.getLogger("IsolatedScanner")
console = Console()


def scan_plugin_isolated(plugin_path: str, plugin_name: str, plugin_type: str, timeout: int = 30, verbose: bool = False) -> dict:
    """
    Scan a single plugin in complete isolation using subprocess.
    
    Args:
        plugin_path: Path to the plugin
        plugin_name: Name of the plugin
        plugin_type: Type of plugin (vst3, aufx)
        timeout: Timeout in seconds
        
    Returns:
        Dictionary with plugin data or error information
    """
    try:
        # Run scan_single.py as a completely separate process
        cmd = [
            sys.executable,
            "-m", 
            "pedalboard_pluginary.scan_single",
            plugin_path,
            plugin_name,
            plugin_type
        ]
        
        if verbose:
            logger.debug(f"Executing isolated scan: {' '.join(cmd)}")
        
        # Run with timeout and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, 'PYTHONWARNINGS': 'ignore'}
        )
        
        if verbose and result.stderr:
            logger.debug(f"Scan stderr for {plugin_name}: {result.stderr}")
        
        if result.stdout:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "path": plugin_path,
                    "name": plugin_name,
                    "type": plugin_type,
                    "error": f"Invalid JSON output: {result.stdout[:100]}"
                }
        else:
            return {
                "success": False,
                "path": plugin_path,
                "name": plugin_name,
                "type": plugin_type,
                "error": f"No output from scanner (exit code: {result.returncode})"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "path": plugin_path,
            "name": plugin_name,
            "type": plugin_type,
            "error": f"Scan timed out after {timeout} seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "path": plugin_path,
            "name": plugin_name,
            "type": plugin_type,
            "error": str(e)
        }


class IsolatedPedalboardScanner:
    """Scanner with complete process isolation for each plugin."""
    
    RE_AUFX = re.compile(r"aufx\s+(\w+)\s+(\w+)\s+-\s+(.*?):\s+(.*?)\s+\((.*?)\)")
    
    def __init__(self, max_workers: Optional[int] = None, timeout: int = 30, verbose: bool = False):
        self.plugins_path = get_cache_path("plugins")
        self.plugins = {}
        self.failed_plugins = {}
        self.max_workers = max_workers or min(mp.cpu_count(), 8)
        self.timeout = timeout
        self.verbose = verbose
        self.ensure_ignores()
        
        if self.verbose:
            logger.setLevel(logging.DEBUG)
            console.print(f"[dim]IsolatedPedalboardScanner initialized:[/dim]")
            console.print(f"  [dim]• Max workers: {self.max_workers}[/dim]")
            console.print(f"  [dim]• Timeout: {self.timeout}s[/dim]")
            console.print(f"  [dim]• Cache path: {self.plugins_path}[/dim]")
        
    def ensure_ignores(self):
        """Ensure ignores file exists."""
        self.ignores_path = get_cache_path("ignores")
        if self.ignores_path.is_dir():
            shutil.rmtree(self.ignores_path)
        if not self.ignores_path.exists():
            copy_default_ignores(self.ignores_path)
        self.ignores = load_ignores(self.ignores_path)
    
    def save_plugins(self):
        """Save plugins and failed plugins to cache."""
        ensure_folder(self.plugins_path)
        save_json_file(dict(sorted(self.plugins.items())), self.plugins_path)
        
        if self.failed_plugins:
            failed_path = get_cache_path("failed_plugins")
            save_json_file(self.failed_plugins, failed_path)
    
    def _list_aufx_plugins(self) -> List[str]:
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
        except (subprocess.CalledProcessError, FileNotFoundError):
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
    
    def _get_vst3_folders(self, extra_folders=None) -> List[Path]:
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
        """
        Scan plugins in parallel with complete process isolation.
        
        Args:
            plugin_tasks: List of (path, name, type, vendor) tuples
        """
        total_tasks = len(plugin_tasks)
        
        if total_tasks == 0:
            console.print("[yellow]No plugins to scan[/yellow]")
            return
        
        console.print(f"\n[cyan]🔍 Scanning {total_tasks} plugins with process isolation...[/cyan]")
        
        # Create progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=False
        ) as progress:
            
            main_task = progress.add_task(
                "[cyan]Scanning plugins", total=total_tasks
            )
            
            completed = 0
            failed = 0
            
            # Use ThreadPoolExecutor for subprocess calls
            # (ProcessPoolExecutor would be overkill since we're already using subprocesses)
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_task = {}
                for path, name, plugin_type, vendor in plugin_tasks:
                    future = executor.submit(
                        scan_plugin_isolated, 
                        str(path), 
                        name, 
                        plugin_type,
                        self.timeout,
                        self.verbose
                    )
                    future_to_task[future] = (path, name, plugin_type, vendor)
                
                # Process completed tasks
                for future in as_completed(future_to_task):
                    path, name, plugin_type, vendor = future_to_task[future]
                    
                    try:
                        result = future.result(timeout=1)
                        
                        if result.get("success", False):
                            # Store successful plugin
                            plugin_entry = {
                                "name": name,
                                "path": str(path),
                                "filename": Path(path).stem,
                                "type": plugin_type,
                                "params": result.get("params", {}),
                            }
                            
                            # Add manufacturer if available
                            if result.get("manufacturer"):
                                plugin_entry["manufacturer"] = result["manufacturer"]
                            elif vendor:
                                plugin_entry["manufacturer"] = vendor
                            
                            # Add metadata if available
                            if result.get("metadata"):
                                plugin_entry["metadata"] = result["metadata"]
                            
                            self.plugins[name] = plugin_entry
                            completed += 1
                        else:
                            # Store failed plugin info
                            self.failed_plugins[name] = {
                                "path": str(path),
                                "type": plugin_type,
                                "error": result.get("error", "Unknown error")
                            }
                            failed += 1
                            
                    except Exception as e:
                        self.failed_plugins[name] = {
                            "path": str(path),
                            "type": plugin_type,
                            "error": str(e)
                        }
                        failed += 1
                    
                    # Update progress
                    progress.update(
                        main_task, 
                        advance=1,
                        description=f"[cyan]Scanning plugins [green]{completed} OK [red]{failed} failed"
                    )
                    
                    # Save periodically
                    if (completed + failed) % 10 == 0:
                        self.save_plugins()
        
        # Final save
        self.save_plugins()
        
        # Report results
        console.print(f"\n[green]✓[/green] Successfully scanned {completed} plugins")
        if failed > 0:
            console.print(f"[red]✗[/red] Failed to scan {failed} plugins")
            console.print(f"   See {get_cache_path('failed_plugins')} for details")
    
    def scan(self, extra_folders=None):
        """Scan all plugins with complete process isolation."""
        # Collect all plugin tasks
        plugin_tasks = []
        
        # VST3 plugins
        vst3_plugins = self._find_vst3_plugins(extra_folders=extra_folders)
        if self.verbose and vst3_plugins:
            console.print(f"[dim]Getting names for {len(vst3_plugins)} VST3 plugins...[/dim]")
        
        for plugin_path in vst3_plugins:
            try:
                # Get plugin names without loading the plugin
                # Use repr to safely pass the path
                path_str = str(plugin_path)
                code = f"import pedalboard; names = pedalboard.VST3Plugin.get_plugin_names_for_file({repr(path_str)}); print('\\n'.join(names))"
                
                if self.verbose:
                    logger.debug(f"Getting plugin names for: {plugin_path}")
                
                with subprocess.Popen(
                    [sys.executable, "-c", code],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE if self.verbose else subprocess.DEVNULL,
                    text=True
                ) as proc:
                    stdout, stderr = proc.communicate(timeout=5)
                    if stdout:
                        names = [n for n in stdout.strip().split('\n') if n]
                        if self.verbose:
                            console.print(f"[dim]  • {plugin_path.stem}: {len(names)} plugin(s)[/dim]")
                            if stderr:
                                logger.debug(f"stderr for {plugin_path}: {stderr}")
                        for plugin_name in names:
                            plugin_tasks.append((str(plugin_path), plugin_name, "vst3", None))
            except Exception as e:
                # If we can't get plugin names, try with the filename
                plugin_name = plugin_path.stem
                plugin_tasks.append((str(plugin_path), plugin_name, "vst3", None))
                if self.verbose:
                    console.print(f"[yellow]  • Using filename for {plugin_path}: {e}[/yellow]")
        
        # AU plugins (macOS only)
        if platform.system() == "Darwin":
            au_plugins = self._find_aufx_plugins()
            if self.verbose and au_plugins:
                console.print(f"[dim]Getting names for {len(au_plugins)} Audio Unit plugins...[/dim]")
            
            for plugin_path, vendor_name, plugin_name in au_plugins:
                try:
                    # Get plugin names without loading the plugin
                    # Use repr to safely pass the path
                    path_str = str(plugin_path)
                    code = f"import pedalboard; names = pedalboard.AudioUnitPlugin.get_plugin_names_for_file({repr(path_str)}); print('\\n'.join(names))"
                    
                    if self.verbose:
                        logger.debug(f"Getting AU plugin names for: {plugin_path}")
                    
                    with subprocess.Popen(
                        [sys.executable, "-c", code],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE if self.verbose else subprocess.DEVNULL,
                        text=True
                    ) as proc:
                        stdout, stderr = proc.communicate(timeout=5)
                        if stdout:
                            names = [n for n in stdout.strip().split('\n') if n]
                            if self.verbose:
                                console.print(f"[dim]  • {plugin_name} by {vendor_name}: {len(names)} plugin(s)[/dim]")
                                if stderr:
                                    logger.debug(f"stderr for {plugin_path}: {stderr}")
                            for name in names:
                                plugin_tasks.append((str(plugin_path), name, "aufx", vendor_name))
                except Exception as e:
                    # Fallback to plugin name from auval
                    plugin_tasks.append((str(plugin_path), plugin_name, "aufx", vendor_name))
                    if self.verbose:
                        console.print(f"[yellow]  • Using auval name for {plugin_name}: {e}[/yellow]")
        
        # Scan in parallel with process isolation
        self.scan_plugins_parallel(plugin_tasks)
    
    def rescan(self, extra_folders=None):
        """Clear cache and rescan all plugins."""
        self.plugins = {}
        self.failed_plugins = {}
        self.scan(extra_folders=extra_folders)
    
    def update(self, extra_folders=None):
        """Update with only new plugins."""
        console.print("\n[cyan]🔍 Scanning for new plugins...[/cyan]")
        
        if not self.plugins_path.exists():
            self.rescan(extra_folders=extra_folders)
            return
        
        self.plugins = load_json_file(self.plugins_path)
        existing_count = len(self.plugins)
        
        # Scan for new plugins
        self.scan(extra_folders=extra_folders)
        
        new_count = len(self.plugins) - existing_count
        if new_count > 0:
            console.print(f"[green]✓[/green] Found {new_count} new plugins")
        else:
            console.print("[yellow]No new plugins found[/yellow]")