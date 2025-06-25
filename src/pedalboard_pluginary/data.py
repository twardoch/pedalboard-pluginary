import json
import os
import platform
import shutil
from importlib import resources
from pathlib import Path
from typing import Any, Dict, List, Set, Union

from .utils import ensure_folder

APP_NAME: str = "com.twardoch.pedalboard-pluginary"
PLUGINS_CACHE_FILENAME_BASE: str = "plugins"  # To identify the plugins cache file


def get_cache_path(cache_name: str) -> Path:
    """Get the path to a cache file."""
    os_name = platform.system()
    if os_name == "Windows":
        app_data_env = os.getenv("APPDATA")
        if app_data_env is None:
            app_data_dir = (
                Path(os.path.expanduser("~")) / "AppData" / "Roaming" / APP_NAME
            )
        else:
            app_data_dir = Path(app_data_env) / APP_NAME
    elif os_name == "Darwin":  # macOS
        app_data_dir = Path.home() / "Library" / "Application Support" / APP_NAME
    else:  # Linux and other Unix-like systems
        xdg_cache_home_env = os.getenv("XDG_CACHE_HOME")
        if xdg_cache_home_env:
            app_data_dir = Path(xdg_cache_home_env) / APP_NAME
        else:
            app_data_dir = Path.home() / ".cache" / APP_NAME

    app_data_dir.mkdir(parents=True, exist_ok=True)  # Ensure base app dir exists
    return app_data_dir / f"{cache_name}.json"


def load_json_file(file_path: Path) -> Any:
    """Load JSON data from a file."""
    if not file_path.exists():
        return {}

    with open(file_path, "r", encoding="utf-8") as file:
        try:
            raw_data = json.load(file)
        except json.JSONDecodeError:
            return {}  # Return empty dict if JSON is corrupted

    return raw_data


def save_json_file(data: Union[Dict[Any, Any], List[Any]], file_path: Path) -> None:
    """Save JSON data to a file."""
    ensure_folder(file_path.parent)
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def load_ignores(ignores_path: Path) -> Set[str]:
    """Load ignores data (list of strings) from the file."""
    content = load_json_file(ignores_path)
    if isinstance(content, list):  # Expects a list of strings
        return set(item for item in content if isinstance(item, str))
    return set()


def save_ignores(ignores: Set[str], ignores_path: Path) -> None:
    """Save ignores data to the file."""
    save_json_file(sorted(list(ignores)), ignores_path)


def copy_default_ignores(destination_path: Path) -> None:
    """Copy the default ignores file to the destination if it does not exist."""
    try:
        import importlib.resources

        default_ignores_src_path = importlib.resources.files(
            "pedalboard_pluginary.resources"
        ).joinpath("default_ignores.json")

        if not destination_path.exists():
            ensure_folder(destination_path.parent)
            with importlib.resources.as_file(
                default_ignores_src_path
            ) as src_file_on_fs:
                if src_file_on_fs.exists():
                    shutil.copy(src_file_on_fs, destination_path)
                else:
                    save_json_file([], destination_path)
    except (ImportError, FileNotFoundError, TypeError) as e:
        print(
            f"Warning: Could not copy default ignores using importlib.resources: {e}. Creating empty ignores file."
        )
        if not destination_path.exists():
            ensure_folder(destination_path.parent)
            save_json_file([], destination_path)