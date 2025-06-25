#!/usr/bin/env python3
# benedict might also lack stubs.
import json
import logging  # For basicConfig
import sys  # For sys.stdout in Display lambda
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import fire
import yaml

# fire library might not have complete type stubs, common to ignore if problematic for mypy.
# Consider adding types-fire if available and it resolves issues.
from benedict import benedict as bdict

from .core import PedalboardPluginary
from .data import (
    PLUGINS_CACHE_FILENAME_BASE,
    get_cache_path,
    load_json_file,
    save_json_file,
)
from .models import PluginInfo
from .types import SerializedPlugin
from .scanner import PedalboardScanner

# Define a more specific type for extra_folders if it's always List[str] after split
ExtraFoldersType = Optional[List[str]]


def setup_logging(verbose_level: int = 0) -> None:
    """Configures basic logging for CLI output."""
    # verbose_level: 0 = WARNING, 1 = INFO, 2 = DEBUG
    log_level = logging.WARNING
    if verbose_level == 1:
        log_level = logging.INFO
    elif verbose_level >= 2:
        log_level = logging.DEBUG

    # Only configure if no handlers are already set (e.g., by tests or other imports)
    # This basicConfig will go to stderr by default for WARNING and above.
    # For INFO, let's direct to stdout for better CLI experience.
    if not logging.getLogger().hasHandlers():
        if log_level <= logging.INFO:
            # For INFO and DEBUG, use a more verbose format and stdout
            logging.basicConfig(
                stream=sys.stdout,
                level=log_level,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
        else:
            # For WARNING, ERROR, CRITICAL, use stderr and simpler format
            logging.basicConfig(
                level=log_level, format="%(levelname)s: %(name)s: %(message)s"
            )


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
