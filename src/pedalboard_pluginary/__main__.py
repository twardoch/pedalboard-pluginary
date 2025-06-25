#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, List, Optional

import fire
import yaml

from .data import (
    PLUGINS_CACHE_FILENAME_BASE,
    get_cache_path,
    load_json_file,
    save_json_file,
)
from .types import SerializedPlugin
from .scanner import PedalboardScanner


def scan_plugins_cli(extra_folders: Optional[str] = None, verbose: int = 0) -> None:
    """Scans all plugins, optionally including extra folders (comma-separated string)."""
    folders_list: List[str] = extra_folders.split(",") if extra_folders else []
    scanner = PedalboardScanner(specific_paths=folders_list)
    scanner.full_scan()  # This updates scanner.plugins
    if scanner.plugins:  # Only save if we found plugins
        cache_file = get_cache_path(PLUGINS_CACHE_FILENAME_BASE)
        save_json_file(scanner.plugins, cache_file)


def update_plugins_cli(extra_folders: Optional[str] = None, verbose: int = 0) -> None:
    """Updates the plugin cache, optionally including extra folders (comma-separated string)."""
    scan_plugins_cli(extra_folders, verbose)


def list_json_cli() -> Dict[str, SerializedPlugin]:
    """Lists all plugins in JSON format."""
    cache_file = get_cache_path(PLUGINS_CACHE_FILENAME_BASE)
    if not cache_file.exists():
        return {}
    data = load_json_file(cache_file)
    return data if isinstance(data, dict) else {}


def list_yaml_cli() -> str:
    """Lists all plugins in YAML format."""
    plugins = list_json_cli()
    return yaml.dump(plugins, sort_keys=False, indent=2)


def main() -> None:
    """Main entry point for the CLI."""
    fire.Fire({
        "scan": scan_plugins_cli,
        "list": list_json_cli,
        "json": list_json_cli,
        "yaml": list_yaml_cli,
        "update": update_plugins_cli,
    })


if __name__ == "__main__":
    main()
