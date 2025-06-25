import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pedalboard

from .data import (
    copy_default_ignores,
    get_cache_path,
    load_ignores,
    save_json_file,
)
from .exceptions import CacheCorruptedError, PluginScanError
from .models import PluginInfo, PluginParameter
from .progress import TqdmProgress
from .protocols import ProgressReporter
from .scanners.au_scanner import AUScanner
from .scanners.vst3_scanner import VST3Scanner
from .serialization import PluginSerializer
from .utils import ensure_folder, from_pb_param

logger: logging.Logger = logging.getLogger(__name__)


class PedalboardScanner:
    """Main scanner class that coordinates scanning of all plugin types."""

    def __init__(
        self,
        ignore_paths: Optional[List[str]] = None,
        specific_paths: Optional[List[str]] = None,
        progress_reporter: Optional[ProgressReporter] = None,
    ):
        """Initialize the scanner with optional ignore paths and specific paths.
        
        Args:
            ignore_paths: List of regex patterns for paths to ignore.
            specific_paths: List of specific paths to scan.
            progress_reporter: Optional progress reporter instance.
        """
        self.ignore_paths = ignore_paths or []
        self.specific_paths = specific_paths or []
        self.plugins: Dict[str, PluginInfo] = {}
        self.plugins_path = get_cache_path("plugins")
        self.ignores_path = get_cache_path("ignores")
        self.progress_reporter = progress_reporter or TqdmProgress()
        
        # Initialize ignores
        copy_default_ignores(self.ignores_path)
        self.ignores = load_ignores(self.ignores_path)
        
        # Initialize scanners
        self.scanners = [
            AUScanner(
                ignore_paths=self.ignore_paths, specific_paths=self.specific_paths
            ),
            VST3Scanner(
                ignore_paths=self.ignore_paths, specific_paths=self.specific_paths
            ),
        ]
        
        # Load existing plugin data if available
        self.load_data()

    def load_data(self) -> None:
        """Load existing plugin data from cache."""
        try:
            self.plugins = PluginSerializer.load_plugins(self.plugins_path)
        except CacheCorruptedError as e:
            logger.warning(f"Cache corrupted, will perform full scan: {e}")
            self.plugins = {}

    def save_data(self) -> None:
        """Save plugin data to cache."""
        PluginSerializer.save_plugins(self.plugins, self.plugins_path)
        
        # Save updated ignores
        save_json_file(list(self.ignores), self.ignores_path)

    def full_scan(self) -> Dict[str, PluginInfo]:
        """Perform a full scan of all plugin types."""
        self.plugins = {}
        total_files = 0
        
        # First, count all plugin files
        all_plugin_files = []
        for scanner in self.scanners:
            plugin_files = scanner.find_plugin_files()
            all_plugin_files.extend([(scanner, pf) for pf in plugin_files])
            total_files += len(plugin_files)
        
        # Scan all plugins with progress reporting
        self.progress_reporter.start(total_files, "Scanning plugins")
        
        for scanner, plugin_file in all_plugin_files:
            plugin_key = f"{scanner.__class__.__name__.replace('Scanner', '').lower()}:{plugin_file}"
            
            # Skip ignored plugins
            if plugin_key in self.ignores:
                logger.info(f"Skipping ignored plugin: {plugin_file}")
                self.progress_reporter.update(1, f"Skipped: {plugin_file.name}")
                continue
            
            try:
                plugin_info = scanner.scan_plugin(plugin_file)
                if plugin_info:
                    self.plugins[plugin_info.id] = plugin_info
                    logger.info(f"Scanned plugin: {plugin_file}")
                    self.progress_reporter.update(1, f"Scanned: {plugin_info.name}")
                else:
                    self.progress_reporter.update(1)
            except PluginScanError as e:
                logger.error(f"Failed to scan plugin {plugin_file}: {e}")
                self.ignores.add(plugin_key)
                self.progress_reporter.update(1, f"Failed: {plugin_file.name}")
            except Exception as e:
                logger.error(f"Unexpected error scanning {plugin_file}: {e}")
                self.ignores.add(plugin_key)
                self.progress_reporter.update(1, f"Error: {plugin_file.name}")
        
        self.progress_reporter.finish(f"Scanned {len(self.plugins)} plugins")
        
        # Save the results
        self.save_data()
        return self.plugins

    def update_scan(self) -> Dict[str, PluginInfo]:
        """Update the scan with new plugins while preserving existing data."""
        # Keep track of existing plugins
        existing_plugins = set(self.plugins.keys())
        new_plugins = {}
        
        # Find all plugin files
        all_plugin_files = []
        for scanner in self.scanners:
            plugin_files = scanner.find_plugin_files()
            all_plugin_files.extend([(scanner, pf) for pf in plugin_files])
        
        # Only scan plugins that aren't already in the cache
        plugins_to_scan = []
        for scanner, plugin_file in all_plugin_files:
            plugin_type = scanner.__class__.__name__.replace('Scanner', '').lower()
            plugin_key = f"{plugin_type}:{plugin_file}"
            
            if plugin_key not in existing_plugins and plugin_key not in self.ignores:
                plugins_to_scan.append((scanner, plugin_file, plugin_key))
        
        # Scan new plugins with progress reporting
        if plugins_to_scan:
            self.progress_reporter.start(len(plugins_to_scan), "Scanning new plugins")
            
            for scanner, plugin_file, plugin_key in plugins_to_scan:
                try:
                    plugin_info = scanner.scan_plugin(plugin_file)
                    if plugin_info:
                        self.plugins[plugin_info.id] = plugin_info
                        new_plugins[plugin_info.id] = plugin_info
                        logger.info(f"Scanned new plugin: {plugin_file}")
                        self.progress_reporter.update(1, f"Scanned: {plugin_info.name}")
                    else:
                        self.progress_reporter.update(1)
                except PluginScanError as e:
                    logger.error(f"Failed to scan plugin {plugin_file}: {e}")
                    self.ignores.add(plugin_key)
                    self.progress_reporter.update(1, f"Failed: {plugin_file.name}")
                except Exception as e:
                    logger.error(f"Unexpected error scanning {plugin_file}: {e}")
                    self.ignores.add(plugin_key)
                    self.progress_reporter.update(1, f"Error: {plugin_file.name}")
            
            self.progress_reporter.finish(f"Found {len(new_plugins)} new plugins")
            
            # Save updated data
            self.save_data()
        
        return new_plugins

    def get_json(self) -> str:
        """Return the plugins data as a JSON string."""
        # Use the serializer to convert plugins to dict format
        plugins_dict = {}
        for key, plugin_info in self.plugins.items():
            plugins_dict[key] = PluginSerializer.plugin_to_dict(plugin_info)
        
        return json.dumps(plugins_dict, indent=2)