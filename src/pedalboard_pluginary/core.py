import json
from pathlib import Path
from .data import load_json_file, get_cache_path
from .scanner import PedalboardScanner

class PedalboardPluginary:
    def __init__(self):
        self.plugins_path = get_cache_path("plugins")
        self.load_data()

    def load_data(self):
        if not self.plugins_path.exists():
            scanner = PedalboardScanner()
            scanner.scan()
        self.plugins = load_json_file(self.plugins_path)

    def list_plugins(self):
        return json.dumps(self.plugins, indent=4)
