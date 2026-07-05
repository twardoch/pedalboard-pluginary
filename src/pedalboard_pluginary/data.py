# this_file: src/pedalboard_pluginary/data.py
from __future__ import annotations

import json
import os
import platform
from collections.abc import Iterable
from importlib import resources
from pathlib import Path
from typing import Any

from .utils import ensure_folder

APP_NAME = "com.twardoch.pedalboard-pluginary"


def get_cache_path(cache_name: str) -> Path:
    """Get the path to a cache file, dispatching on the current platform."""
    system = platform.system()
    if system == "Windows":
        cache_folder = Path(os.getenv("APPDATA", str(Path.home()))) / APP_NAME
    elif system == "Darwin":
        cache_folder = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        xdg_cache_home = os.getenv("XDG_CACHE_HOME")
        base = Path(xdg_cache_home) if xdg_cache_home else Path.home() / ".cache"
        cache_folder = base / APP_NAME
    # The caller passes the full filename (e.g. "plugins.db"); don't append a suffix.
    return cache_folder / cache_name


def load_json_file(file_path: Path) -> Any:
    """Load JSON data from a file."""
    if file_path.exists():
        with open(file_path) as file:
            return json.load(file)
    return {}


def save_json_file(data: Any, file_path: Path) -> None:
    """Save JSON data to a file."""
    ensure_folder(file_path)
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)


def load_ignores(ignores_path: Path) -> set[str]:
    """Load ignores data from the file."""
    return set(load_json_file(ignores_path))


def save_ignores(ignores: Iterable[str], ignores_path: Path) -> None:
    """Save ignores data to the file."""
    save_json_file(sorted(list(ignores)), ignores_path)


def copy_default_ignores(destination_path: Path) -> None:
    """Copy the default ignores file to the destination if it does not exist."""
    if not destination_path.exists():
        ensure_folder(destination_path)
        # Use importlib.resources to access the default ignores file
        with resources.open_text(
            "pedalboard_pluginary.resources", "default_ignores.json"
        ) as f:
            with open(destination_path, "w") as dest:
                dest.write(f.read())
