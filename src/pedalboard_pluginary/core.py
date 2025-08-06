from __future__ import annotations

from .cache.sqlite_backend import SQLiteCacheBackend
from .data import get_cache_path
from .scanner_isolated import IsolatedPedalboardScanner


class PedalboardPluginary:
    """
    Main class for interacting with the plugin library.
    Provides a high-level API for scanning and accessing plugin data.
    """

    def __init__(self, **scanner_kwargs):
        self.cache = SQLiteCacheBackend(db_path=get_cache_path("plugins.db"))
        self.scanner = IsolatedPedalboardScanner(**scanner_kwargs)

    def scan(self, rescan: bool = False, extra_folders: list[str] | None = None):
        """
        Initiates a plugin scan.

        Args:
            rescan: If True, clears the cache before scanning.
            extra_folders: A list of additional folders to scan for plugins.
        """
        self.scanner.scan(rescan=rescan, extra_folders=extra_folders)

    def list_plugins(self, **filters) -> list[dict]:
        """Lists plugins from the cache, optionally applying filters."""
        # Load all plugins from cache
        all_plugins = self.cache.load()
        
        # Convert to list of dicts
        plugin_list = []
        for plugin_id, plugin in all_plugins.items():
            plugin_dict = {
                "id": plugin.id,
                "name": plugin.name,
                "path": plugin.path,
                "type": plugin.plugin_type,
                "manufacturer": plugin.manufacturer,
                "params": {k: v.value for k, v in plugin.parameters.items()} if plugin.parameters else {}
            }
            
            # Apply filters if provided
            if filters:
                # Check name filter
                if "name" in filters and filters["name"]:
                    if filters["name"].lower() not in plugin.name.lower():
                        continue
                
                # Check manufacturer filter
                if "manufacturer" in filters and filters["manufacturer"]:
                    if not plugin.manufacturer or filters["manufacturer"].lower() not in plugin.manufacturer.lower():
                        continue
                
                # Check type filter
                if "type" in filters and filters["type"]:
                    if plugin.plugin_type != filters["type"]:
                        continue
            
            plugin_list.append(plugin_dict)
        
        return plugin_list

    def get_plugin_details(self, plugin_id: str) -> dict | None:
        """Retrieves detailed information for a single plugin."""
        all_plugins = self.cache.load()
        if plugin_id in all_plugins:
            plugin = all_plugins[plugin_id]
            return {
                "id": plugin.id,
                "name": plugin.name,
                "path": plugin.path,
                "type": plugin.plugin_type,
                "manufacturer": plugin.manufacturer,
                "params": {k: v.value for k, v in plugin.parameters.items()} if plugin.parameters else {}
            }
        return None