import itertools
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import warnings
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from urllib.parse import unquote, urlparse

import pedalboard
from rich.console import Console
from rich.live import Live
from rich.table import Table

from .data import (
    copy_default_ignores,
    get_cache_path,
    load_ignores,
    load_json_file,
    save_json_file,
)
from .utils import ensure_folder, from_pb_param

# Configure logging to be less verbose
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("Scanner")
console = Console()

# Suppress warnings
warnings.filterwarnings("ignore")

@contextmanager
def suppress_output():
    """Context manager to suppress stdout and stderr."""
    with StringIO() as buf_out, StringIO() as buf_err:
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            yield


class PedalboardScanner:
    RE_AUFX = re.compile(r"aufx\s+(\w+)\s+(\w+)\s+-\s+(.*?):\s+(.*?)\s+\((.*?)\)")

    def __init__(self):
        self.plugins_path = get_cache_path("plugins")
        self.plugins = {}
        self.safe_save = True
        self.ensure_ignores()

    def ensure_ignores(self):
        self.ignores_path = get_cache_path("ignores")
        if self.ignores_path.is_dir(): # If it exists as a directory
            logger.warning(f"'{self.ignores_path}' is a directory, removing it.")
            shutil.rmtree(self.ignores_path) # Remove the directory
        if not self.ignores_path.exists(): # Now, if it doesn't exist (as file or dir)
            copy_default_ignores(self.ignores_path)
        self.ignores = load_ignores(self.ignores_path)

    def save_plugins(self):
        ensure_folder(self.plugins_path)
        save_json_file(dict(sorted(self.plugins.items())), self.plugins_path)

    def _list_aufx_plugins(self):
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

    def _find_aufx_plugins(self, plugin_paths=None):
        if plugin_paths:
            # Extract just the paths if we have tuples
            plugin_paths = [
                Path(p[0] if isinstance(p, tuple) else p).resolve() 
                for p in plugin_paths
            ]
        aufx_plugins = []
        plugin_type = "aufx"
        for line in self._list_aufx_plugins():
            match = self.RE_AUFX.match(line)
            if match:
                (
                    plugin_code,
                    vendor_code,
                    vendor_name,
                    plugin_name,
                    plugin_url,
                ) = match.groups()
                plugin_path = Path(unquote(urlparse(plugin_url).path)).resolve()
                plugin_fn = plugin_path.stem
                plugin_key = f"{plugin_type}/{plugin_fn}"
                if plugin_key not in self.ignores:
                    if plugin_paths and plugin_path not in plugin_paths:
                        continue
                    # Store plugin path with vendor info
                    aufx_plugins.append((plugin_path, vendor_name))
        return aufx_plugins

    def _get_vst3_folders(self, extra_folders=None):
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

    def _find_vst3_plugins(self, extra_folders=None, plugin_paths=None):
        vst3_plugins = []
        plugin_type = "vst3"
        if plugin_paths:
            plugin_paths = [Path(p).resolve() for p in plugin_paths]

        plugin_paths = plugin_paths or list(
            itertools.chain.from_iterable(
                folder.glob(f"*.{plugin_type}")
                for folder in self._get_vst3_folders(extra_folders=extra_folders)
            )
        )
        for plugin_path in plugin_paths:
            plugin_fn = plugin_path.stem
            plugin_key = f"{plugin_type}/{plugin_fn}"
            if plugin_key not in self.ignores:
                vst3_plugins.append(plugin_path)
        return vst3_plugins

    def get_plugin_info(self, plugin_path, plugin_name):
        """Get plugin parameters and metadata."""
        # Suppress plugin loading output
        with suppress_output():
            plugin = pedalboard.load_plugin(str(plugin_path), plugin_name=plugin_name)
            plugin_params = {
                k: from_pb_param(plugin.__getattr__(k)) for k in plugin.parameters.keys()
            }
            
            # Extract manufacturer/vendor info
            manufacturer = None
            if hasattr(plugin, 'manufacturer'):
                manufacturer = plugin.manufacturer
            
        return plugin_params, manufacturer

    def scan_typed_plugin_path(
        self, plugin_type, plugin_key, plugin_path, plugin_fn, plugin_loader
    ):
        plugin_path = str(plugin_path)
        try:
            plugin_names = plugin_loader.get_plugin_names_for_file(plugin_path)
            for plugin_name in plugin_names:
                if plugin_name in self.plugins:
                    continue
                plugin_params, manufacturer = self.get_plugin_info(plugin_path, plugin_name)
                plugin_entry = {
                    "name": plugin_name,
                    "path": plugin_path,
                    "filename": plugin_fn,
                    "type": plugin_type,
                    "params": plugin_params,
                }
                if manufacturer:
                    plugin_entry["manufacturer"] = manufacturer
                self.plugins[plugin_name] = plugin_entry
        except (ImportError, Exception) as e:
            logger.warning(f"Failed to scan plugin {plugin_path}: {e}")

    def scan_typed_plugins(self, plugin_type, found_plugins, plugin_loader):
        """Scan plugins with a beautiful live Rich table display."""
        total_plugins = len(found_plugins)
        
        if total_plugins == 0:
            return
            
        # Create a minimalist table without borders or headers
        def create_progress_table(current_idx, current_plugin_path, current_vendor=None):
            table = Table(show_header=False, box=None, padding=(0, 1))
            
            # Add columns without headers
            table.add_column(style="cyan", width=50)  # Plugin path
            table.add_column(style="yellow", width=25)  # Vendor
            table.add_column(style="green", width=15)  # Progress
            
            # Show current plugin being scanned
            if current_plugin_path:
                plugin_name = Path(current_plugin_path).stem
                # Truncate long plugin names
                if len(plugin_name) > 45:
                    plugin_name = plugin_name[:42] + "..."
                    
                vendor_text = current_vendor if current_vendor else "scanning..."
                # Truncate long vendor names
                if len(vendor_text) > 22:
                    vendor_text = vendor_text[:19] + "..."
                    
                progress_text = f"{current_idx + 1}/{total_plugins}"
                
                table.add_row(
                    f"  {plugin_name}",
                    vendor_text,
                    progress_text
                )
                
            return table
        
        with Live(create_progress_table(0, None), console=console, refresh_per_second=10, transient=False) as live:
            for idx, plugin_item in enumerate(found_plugins):
                # Handle both tuple (path, vendor) for AU and plain path for VST3
                if isinstance(plugin_item, tuple):
                    plugin_path, auval_vendor = plugin_item
                else:
                    plugin_path = plugin_item
                    auval_vendor = None
                    
                plugin_fn = str(Path(plugin_path).stem)
                plugin_key = f"{plugin_type}/{plugin_fn}"
                
                # Update the live display with current plugin (show auval vendor if available)
                live.update(create_progress_table(idx, plugin_path, auval_vendor))
                
                # Scan the plugin and get vendor info
                plugin_path_str = str(plugin_path)
                vendor = auval_vendor  # Start with auval vendor if available
                
                try:
                    with suppress_output():
                        plugin_names = plugin_loader.get_plugin_names_for_file(plugin_path_str)
                    for plugin_name in plugin_names:
                        if plugin_name in self.plugins:
                            continue
                        plugin_params, manufacturer = self.get_plugin_info(plugin_path_str, plugin_name)
                        
                        # Use manufacturer from plugin if available, otherwise use auval vendor
                        if manufacturer:
                            vendor = manufacturer
                        elif auval_vendor:
                            vendor = auval_vendor
                        
                        plugin_entry = {
                            "name": plugin_name,
                            "path": plugin_path_str,
                            "filename": plugin_fn,
                            "type": plugin_type,
                            "params": plugin_params,
                        }
                        if vendor:
                            plugin_entry["manufacturer"] = vendor
                        self.plugins[plugin_name] = plugin_entry
                        
                        # Update display with vendor info
                        live.update(create_progress_table(idx, plugin_path, vendor))
                        
                except (ImportError, Exception) as e:
                    logger.warning(f"Failed to scan plugin {plugin_path}: {e}")
                
                if self.safe_save:
                    self.save_plugins()

    def scan_aufx_plugins(self, plugin_paths=None):
        # If plugin_paths is provided (from update method), use them directly
        # Otherwise get all AU plugins with _find_aufx_plugins
        if plugin_paths is not None:
            plugins_to_scan = plugin_paths
        else:
            plugins_to_scan = list(self._find_aufx_plugins())
        
        self.scan_typed_plugins(
            "aufx",
            plugins_to_scan,
            pedalboard.AudioUnitPlugin,
        )

    def scan_vst3_plugins(self, extra_folders=None, plugin_paths=None):
        self.scan_typed_plugins(
            "vst3",
            list(
                self._find_vst3_plugins(
                    extra_folders=extra_folders, plugin_paths=plugin_paths
                )
            ),
            pedalboard.VST3Plugin,
        )

    def scan_plugins(self, extra_folders=None, plugin_paths=None):
        self.scan_vst3_plugins(extra_folders=extra_folders, plugin_paths=plugin_paths)
        if platform.system() == "Darwin":
            self.scan_aufx_plugins(plugin_paths=plugin_paths)

    def scan(self, extra_folders=None, plugin_paths=None):
        console.print("\n[cyan]🔍 Scanning plugins...[/cyan]")
        self.scan_plugins(extra_folders=None, plugin_paths=plugin_paths)
        self.save_plugins()
        
        # Show summary
        total = len(self.plugins)
        vst3_count = sum(1 for p in self.plugins.values() if p.get("type") == "vst3")
        au_count = sum(1 for p in self.plugins.values() if p.get("type") == "aufx")
        
        console.print(f"\n[green]✓[/green] Scan complete! Found {total} plugins ({vst3_count} VST3, {au_count} AU)")

    def rescan(self, extra_folders=None):
        self.plugins = {}
        self.scan(extra_folders=extra_folders)

    def update(self, extra_folders=None):
        console.print("\n[cyan]🔍 Scanning for new plugins...[/cyan]")
        if not self.plugins_path.exists():
            self.rescan(extra_folders=extra_folders)
            return
        self.plugins = load_json_file(self.plugins_path)
        existing_count = len(self.plugins)
        new_vst3_paths = sorted(
            list(
                set(self._find_vst3_plugins(extra_folders=extra_folders))
                - {
                    Path(p["path"]).resolve()
                    for p in self.plugins.values()
                    if p["type"] == "vst3"
                }
            )
        )
        self.scan_vst3_plugins(extra_folders=extra_folders, plugin_paths=new_vst3_paths)
        
        # For AU plugins, we need to handle the tuple format (path, vendor)
        aufx_plugins_with_vendor = self._find_aufx_plugins()
        existing_aufx_paths = {
            Path(p["path"]).resolve()
            for p in self.plugins.values()
            if p["type"] == "aufx"
        }
        
        new_aufx_plugins = []
        for plugin_info in aufx_plugins_with_vendor:
            plugin_path = plugin_info[0] if isinstance(plugin_info, tuple) else plugin_info
            if plugin_path not in existing_aufx_paths:
                new_aufx_plugins.append(plugin_info)
        
        if platform.system() == "Darwin" and new_aufx_plugins:
            self.scan_aufx_plugins(plugin_paths=new_aufx_plugins)
        self.save_plugins()
        
        # Show summary
        new_count = len(self.plugins) - existing_count
        if new_count > 0:
            console.print(f"\n[green]✓[/green] Found {new_count} new plugins")
        else:
            console.print("\n[yellow]No new plugins found[/yellow]")

    def get_json(self):
        return json.dumps(self.plugins, indent=4)
