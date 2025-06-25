import json
from pathlib import Path
from typing import Dict

from .data import get_cache_path
from .models import PluginInfo
from .scanner import PedalboardScanner
from .serialization import PluginSerializer


class PedalboardPluginary:
    """Main class for the Pedalboard Pluginary application."""
    
    plugins_path: Path
    plugins: Dict[str, PluginInfo]

    def __init__(self) -> None:
        """Initialize the Pedalboard Pluginary instance."""
        self.plugins_path = get_cache_path("plugins")
        self.plugins = {}
        self.load_data()

    def load_data(self) -> None:
        """Load plugin data from cache or perform a scan if cache doesn't exist."""
        if not self.plugins_path.exists():
            scanner = PedalboardScanner()
            scanner.full_scan()

        # Load plugins using the serializer
        self.plugins = PluginSerializer.load_plugins(self.plugins_path)

    def list_plugins(self) -> str:
        """Returns a JSON string representation of the plugins."""
        # Convert PluginInfo objects to dictionaries for JSON serialization
        plugins_dict = {}
        for plugin_id, plugin in self.plugins.items():
            plugins_dict[plugin_id] = PluginSerializer.plugin_to_dict(plugin)
        
        return json.dumps(plugins_dict, indent=4)