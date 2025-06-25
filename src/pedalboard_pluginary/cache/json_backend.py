"""JSON cache backend for backward compatibility."""

from typing import Dict
from pathlib import Path

from ..models import PluginInfo
from ..protocols import CacheBackend
from ..serialization import PluginSerializer


class JSONCacheBackend(CacheBackend):
    """Legacy JSON cache backend for backward compatibility."""
    
    def __init__(self, json_path: Path):
        self.json_path = json_path
    
    def load(self) -> Dict[str, PluginInfo]:
        """Load plugins from JSON cache."""
        return PluginSerializer.load_plugins(self.json_path)
    
    def save(self, plugins: Dict[str, PluginInfo]) -> None:
        """Save plugins to JSON cache."""
        PluginSerializer.save_plugins(plugins, self.json_path)
    
    def update(self, plugin_id: str, plugin: PluginInfo) -> None:
        """Update a single plugin in JSON cache."""
        plugins = self.load()
        plugins[plugin_id] = plugin
        self.save(plugins)
    
    def delete(self, plugin_id: str) -> None:
        """Remove a plugin from JSON cache."""
        plugins = self.load()
        if plugin_id in plugins:
            del plugins[plugin_id]
            self.save(plugins)
    
    def clear(self) -> None:
        """Clear JSON cache."""
        self.save({})
    
    def exists(self) -> bool:
        """Check if JSON cache exists."""
        return self.json_path.exists()