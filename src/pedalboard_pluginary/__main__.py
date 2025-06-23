#!/usr/bin/env python3
import fire # type: ignore[import-untyped]
# fire library might not have complete type stubs, common to ignore if problematic for mypy.
# Consider adding types-fire if available and it resolves issues.

from typing import Optional, List, Any, Callable, Dict
import sys # For sys.stdout in Display lambda

from .core import PedalboardPluginary
from .scanner import PedalboardScanner
from benedict import benedict as bdict # type: ignore[import-untyped]
# benedict might also lack stubs.
import logging # For basicConfig

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
            logging.basicConfig(stream=sys.stdout, level=log_level,
                                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        else:
            # For WARNING, ERROR, CRITICAL, use stderr and simpler format
            logging.basicConfig(level=log_level,
                                format="%(levelname)s: %(name)s: %(message)s")


def scan_plugins_cli(extra_folders: Optional[str] = None, verbose: int = 0) -> None:
    """Scans all plugins, optionally including extra folders (comma-separated string)."""
    folders_list: ExtraFoldersType = extra_folders.split(",") if extra_folders else None
    # The original code passes extra_folders=None to rescan, which seems like a bug.
    # It should pass folders_list.
    setup_logging(verbose)
    PedalboardScanner().rescan(extra_folders=folders_list)


def update_plugins_cli(extra_folders: Optional[str] = None, verbose: int = 0) -> None:
    """Updates plugin list, optionally including extra folders (comma-separated string)."""
    setup_logging(verbose)
    folders_list: ExtraFoldersType = extra_folders.split(",") if extra_folders else None
    # Similar to scan_plugins, original code passes extra_folders=None to update.
    # It should pass folders_list.
    PedalboardScanner().update_scan(extra_folders=folders_list) # Changed to update_scan


def list_json_cli(verbose: int = 0) -> str:
    """Lists all plugins in JSON format."""
    setup_logging(verbose)
    return bdict(PedalboardPluginary().plugins).to_json()


def list_yaml_cli(verbose: int = 0) -> str:
    """Lists all plugins in YAML format."""
    setup_logging(verbose)
    return bdict(PedalboardPluginary().plugins).to_yaml()


def main_cli() -> None: # Renamed from cli to avoid conflict if fire creates a 'cli' command
    """Main CLI entry point. Call with --verbose=1 for INFO, --verbose=2 for DEBUG logs."""
    # Adjusting fire.core.Display to be type-friendly if possible, or type: ignore it.
    # The lambda itself is: `lambda lines, out: print(*lines, file=out)`
    # `lines` is usually a tuple of strings, `out` is a file-like object.
    display_lambda: Callable[[tuple[str, ...], Any], None] = lambda lines, out: print(*lines, file=out)
    fire.core.Display = display_lambda # type: ignore[attr-defined]

    # Fire will automatically expose methods of an object, or items in a dict.
    # We can pass the functions directly. Fire handles the --verbose flag if it's an arg in functions.
    fire_commands: Dict[str, Callable[..., Any]] = {
            "scan": scan_plugins_cli,       # Connects to scan_plugins_cli(extra_folders=None, verbose=0)
            "update": update_plugins_cli,   # Connects to update_plugins_cli(extra_folders=None, verbose=0)
            "list": list_json_cli,          # Default 'list' command
            "json": list_json_cli,          # Explicit 'json' command
            "yaml": list_yaml_cli,
        }
    fire.Fire(fire_commands)


if __name__ == "__main__":
    main_cli()
