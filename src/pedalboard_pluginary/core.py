import json
from pathlib import Path
from typing import Any, Dict

from .data import get_cache_path, load_json_file
from .scanner import PedalboardScanner


class PedalboardPluginary:
    plugins_path: Path
    plugins: Dict[str, Any]  # Assuming plugin names (keys) are strings

    def __init__(self) -> None:
        self.plugins_path = get_cache_path("plugins")
        self.plugins = {}  # Initialize to empty dict
        self.load_data()

    def load_data(self) -> None:
        if not self.plugins_path.exists():
            scanner = PedalboardScanner()
            scanner.full_scan()  # Updated to use full_scan instead of scan

        # Ensure plugins are loaded even if scan wasn't needed or if it just ran
        # load_json_file returns Dict[Any, Any], but we expect Dict[str, Any] for plugins
        loaded_plugins = load_json_file(self.plugins_path)
        if isinstance(loaded_plugins, dict):
            self.plugins = loaded_plugins
        else:
            # This case should ideally not happen if save_json_file and load_json_file are robust
            self.plugins = {}

    def list_plugins(self) -> str:
        """Returns a JSON string representation of the plugins."""
        return json.dumps(self.plugins, indent=4)
