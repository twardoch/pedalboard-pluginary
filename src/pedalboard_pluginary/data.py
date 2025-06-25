import json
import os
import platform  # Added
import shutil
from importlib import resources
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from .models import PluginInfo, PluginParameter  # Added

# pkg_resources import removed, will rely on importlib.resources primarily.
# Fallback block for pkg_resources in copy_default_ignores will try to use it
# and handle NameError if it's not available.
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


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load JSON data from a file. If it's the plugins cache, reconstruct PluginInfo objects."""
    if not file_path.exists():
        return {}

    with open(file_path, "r", encoding="utf-8") as file:
        try:
            raw_data = json.load(file)
        except json.JSONDecodeError:
            return {}  # Return empty dict if JSON is corrupted

    # Check if this is the plugins cache file by its name
    if file_path.name == f"{PLUGINS_CACHE_FILENAME_BASE}.json":
        if not isinstance(raw_data, dict):
            return {}  # Corrupted plugin cache

        reconstructed_plugins: Dict[str, PluginInfo] = {}
        for plugin_id, plugin_data_dict in raw_data.items():
            if not isinstance(plugin_data_dict, dict):
                continue  # Skip malformed entries

            param_dicts = plugin_data_dict.get("parameters", {})
            reconstructed_params: Dict[str, PluginParameter] = {}
            if isinstance(param_dicts, dict):
                for param_name, param_data_dict in param_dicts.items():
                    if isinstance(param_data_dict, dict):
                        try:
                            reconstructed_params[param_name] = PluginParameter(
                                name=str(param_data_dict.get("name", param_name)),
                                value=param_data_dict.get("value", 0.0),
                            )
                        except TypeError as e:
                            print(
                                f"Warning: Could not reconstruct parameter {param_name} for {plugin_id}: {e}"
                            )
                            continue

            try:
                reconstructed_plugins[plugin_id] = PluginInfo(
                    id=plugin_data_dict.get("id", plugin_id),
                    name=plugin_data_dict.get("name", "Unknown Plugin Name"),
                    path=plugin_data_dict.get("path", ""),
                    filename=plugin_data_dict.get("filename", ""),
                    plugin_type=plugin_data_dict.get("plugin_type", "unknown"),
                    parameters=reconstructed_params,
                    manufacturer=plugin_data_dict.get("manufacturer"),
                    name_in_file=plugin_data_dict.get("name_in_file"),
                )
            except TypeError as e:
                print(
                    f"Warning: Could not reconstruct plugin info for {plugin_id}: {e}"
                )
                continue

        return reconstructed_plugins

    # Handle non-plugin cache files
    result: Dict[str, Any] = {}
    if isinstance(raw_data, dict):
        result = {str(k): v for k, v in raw_data.items()}
    elif isinstance(raw_data, list):
        result = {str(i): item for i, item in enumerate(raw_data)}
    return result


def save_json_file(data: Union[Dict[Any, Any], List[Any]], file_path: Path) -> None:
    """Save JSON data to a file."""
    ensure_folder(file_path)
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
            ensure_folder(destination_path)
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
            ensure_folder(destination_path)
            save_json_file([], destination_path)
