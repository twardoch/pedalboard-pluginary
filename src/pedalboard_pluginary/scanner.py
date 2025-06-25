import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

from .scanners.au_scanner import AUScanner
from .scanners.vst3_scanner import VST3Scanner
from .async_scanner import AsyncScannerMixin

import pedalboard

from .constants import DEFAULT_MAX_CONCURRENT
from .data import (
    copy_default_ignores,
    get_cache_path,
    get_sqlite_cache_path,
    load_ignores,
    save_json_file,
)
from .cache import SQLiteCacheBackend, JSONCacheBackend, migrate_json_to_sqlite
from .exceptions import CacheCorruptedError, PluginScanError
from .models import PluginInfo, PluginParameter
from .progress import TqdmProgress
from .protocols import ProgressReporter
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
        async_mode: bool = False,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        use_sqlite: bool = True,
    ):
        """Initialize the scanner with optional ignore paths and specific paths.
        
        Args:
            ignore_paths: List of regex patterns for paths to ignore.
            specific_paths: List of specific paths to scan.
            progress_reporter: Optional progress reporter instance.
            async_mode: Whether to use async scanning for better performance.
            max_concurrent: Maximum number of concurrent scans (async mode only).
            use_sqlite: Whether to use SQLite cache backend (default: True).
        """
        self.ignore_paths = ignore_paths or []
        self.specific_paths = specific_paths or []
        self.plugins: Dict[str, PluginInfo] = {}
        self.progress_reporter = progress_reporter or TqdmProgress()
        self.async_mode = async_mode
        self.max_concurrent = max_concurrent
        self.use_sqlite = use_sqlite
        
        # Initialize cache paths
        self.ignores_path = get_cache_path("ignores")
        
        # Initialize cache backend
        if use_sqlite:
            self.sqlite_path = get_sqlite_cache_path("plugins")
            self.json_path = get_cache_path("plugins")  # For migration
            self.cache_backend = SQLiteCacheBackend(self.sqlite_path)
            
            # Migrate from JSON if SQLite doesn't exist but JSON does
            if not self.sqlite_path.exists() and self.json_path.exists():
                try:
                    migrated_count = migrate_json_to_sqlite(self.json_path, self.sqlite_path)
                    logger.info(f"Migrated {migrated_count} plugins from JSON to SQLite cache")
                except Exception as e:
                    logger.warning(f"Migration failed, starting with empty SQLite cache: {e}")
        else:
            self.json_path = get_cache_path("plugins")
            self.cache_backend = JSONCacheBackend(self.json_path)
        
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

    async def full_scan_async(self) -> Dict[str, PluginInfo]:
        """Perform a full async scan of all plugin types."""
        if not self.async_mode:
            raise ValueError("Async mode not enabled. Set async_mode=True during initialization.")
        
        self.plugins = {}
        
        # Collect all plugin files from all scanners
        all_plugin_files = []
        for scanner in self.scanners:
            plugin_files = scanner.find_plugin_files()
            all_plugin_files.extend(plugin_files)
        
        # Filter out ignored plugins
        files_to_scan = []
        for plugin_file in all_plugin_files:
            # Find the appropriate scanner for this file
            found_scanner = self._find_scanner_for_file(plugin_file)
            if found_scanner:
                plugin_key = f"{found_scanner.__class__.__name__.replace('Scanner', '').lower()}:{plugin_file}"
                if plugin_key not in self.ignores:
                    files_to_scan.append(plugin_file)
        
        # Scan plugins asynchronously
        if files_to_scan:
            # Use the first scanner that supports async (they all do now)
            async_scanner = cast(AsyncScannerMixin, self.scanners[0])  # VST3Scanner and AUScanner both have AsyncScannerMixin
            
            scanned_plugins = []
            async for plugin in async_scanner.scan_plugins_batch(
                files_to_scan, 
                max_concurrent=self.max_concurrent,
                progress_reporter=self.progress_reporter
            ):
                scanned_plugins.append(plugin)
                self.plugins[plugin.id] = plugin
        
        # Save the results
        self.save_data()
        return self.plugins
    
    async def update_scan_async(self) -> Dict[str, PluginInfo]:
        """Update the scan asynchronously with new plugins while preserving existing data."""
        if not self.async_mode:
            raise ValueError("Async mode not enabled. Set async_mode=True during initialization.")
        
        # Keep track of existing plugins
        existing_plugins = set(self.plugins.keys())
        new_plugins = {}
        
        # Find all plugin files
        all_plugin_files = []
        for scanner in self.scanners:
            plugin_files = scanner.find_plugin_files()
            all_plugin_files.extend(plugin_files)
        
        # Only scan plugins that aren't already in the cache
        files_to_scan = []
        for plugin_file in all_plugin_files:
            found_scanner = self._find_scanner_for_file(plugin_file)
            if found_scanner:
                plugin_type = found_scanner.__class__.__name__.replace('Scanner', '').lower()
                plugin_key = f"{plugin_type}:{plugin_file}"
                
                if plugin_key not in existing_plugins and plugin_key not in self.ignores:
                    files_to_scan.append(plugin_file)
        
        # Scan new plugins asynchronously
        if files_to_scan:
            async_scanner = cast(AsyncScannerMixin, self.scanners[0])
            
            async for plugin in async_scanner.scan_plugins_batch(
                files_to_scan,
                max_concurrent=self.max_concurrent,
                progress_reporter=self.progress_reporter
            ):
                self.plugins[plugin.id] = plugin
                new_plugins[plugin.id] = plugin
            
            # Save updated data
            self.save_data()
        
        return new_plugins
    
    def _find_scanner_for_file(self, plugin_file: Path) -> Optional[Union[AUScanner, VST3Scanner]]:
        """Find the appropriate scanner for a given plugin file."""
        for scanner in self.scanners:
            if scanner.validate_plugin_path(plugin_file):
                return scanner  # type: ignore[return-value]
        return None

    def get_json(self) -> str:
        """Return the plugins data as a JSON string."""
        # Use the serializer to convert plugins to dict format
        plugins_dict = {}
        for key, plugin_info in self.plugins.items():
            plugins_dict[key] = PluginSerializer.plugin_to_dict(plugin_info)
        
        return json.dumps(plugins_dict, indent=2)