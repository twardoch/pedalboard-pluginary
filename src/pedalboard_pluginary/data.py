import json
import os
import platform # Added
import shutil
from pathlib import Path
from typing import Any, Dict, List, Set
# pkg_resources import removed, will rely on importlib.resources primarily.
# Fallback block for pkg_resources in copy_default_ignores will try to use it
# and handle NameError if it's not available.

from .utils import ensure_folder
from .models import PluginInfo, PluginParameter # Added

APP_NAME: str = "com.twardoch.pedalboard-pluginary"
PLUGINS_CACHE_FILENAME_BASE: str = "plugins" # To identify the plugins cache file

def get_cache_path(cache_name: str) -> Path:
    """ Get the path to a cache file. """
    app_data_dir: Path
    if os.name == "nt":
        app_data_env = os.getenv("APPDATA")
        if app_data_env is None:
            # Fallback or error if APPDATA is not set, though it usually is on Windows.
            # For simplicity, let's assume it's set, or Path will handle it.
            # A more robust solution would handle app_data_env being None.
            app_data_dir = Path(os.path.expanduser("~")) / "AppData" / "Roaming" / APP_NAME
        else:
            app_data_dir = Path(app_data_env) / APP_NAME
    elif platform.system() == "Darwin": # macOS
        app_data_dir = Path.home() / "Library" / "Application Support" / APP_NAME
    else: # Linux and other Unix-like systems
        xdg_cache_home_env = os.getenv("XDG_CACHE_HOME")
        if xdg_cache_home_env:
            app_data_dir = Path(xdg_cache_home_env) / APP_NAME
        else:
            app_data_dir = Path.home() / ".cache" / APP_NAME

    app_data_dir.mkdir(parents=True, exist_ok=True) # Ensure base app dir exists
    return app_data_dir / f"{cache_name}.json"

def load_json_file(file_path: Path) -> Dict[Any, Any]: # Or more specific if structure is known
    """ Load JSON data from a file. If it's the plugins cache, reconstruct PluginInfo objects. """
    if not file_path.exists():
        return {}

    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            raw_data = json.load(file)
        except json.JSONDecodeError:
            return {} # Return empty dict if JSON is corrupted

    if not isinstance(raw_data, dict): # Expecting a dict for plugin cache or other dict-based JSONs
        if file_path.name == f"{PLUGINS_CACHE_FILENAME_BASE}.json" or isinstance(raw_data, list): # Allow list for ignores
             # If it's the plugin cache but not a dict, or if it's a list (like ignores), it's problematic for plugin cache
             # but potentially fine for ignores. This function is generic, so let specific callers handle type issues.
             # However, for plugin cache, we need a dict.
             if file_path.name == f"{PLUGINS_CACHE_FILENAME_BASE}.json" and not isinstance(raw_data, dict):
                 return {} # Corrupted plugin cache
        else: # Not plugin cache, not list, and not dict.
            return {}


    # Check if this is the plugins cache file by its name
    if file_path.name == f"{PLUGINS_CACHE_FILENAME_BASE}.json":
        reconstructed_plugins: Dict[str, PluginInfo] = {}
        for plugin_id, plugin_data_dict in raw_data.items():
            if not isinstance(plugin_data_dict, dict):
                continue # Skip malformed entries

            param_dicts = plugin_data_dict.get("parameters", {})
            reconstructed_params: Dict[str, PluginParameter] = {}
            if isinstance(param_dicts, dict):
                for param_name, param_data_dict in param_dicts.items():
                    if isinstance(param_data_dict, dict):
                        try:
                            # Ensure all required fields for PluginParameter are present or provide defaults
                            # The 'name' in param_data_dict should match param_name from the key
                            reconstructed_params[param_name] = PluginParameter(
                                name=param_data_dict.get("name", param_name), # Use key as fallback
                                value=param_data_dict.get("value") # Let it be None if missing, handle in PluginParameter if needed
                                # Add other fields like min_value, max_value if they are in models.py and JSON
                            )
                        except TypeError as e: # If 'value' is missing and dataclass requires it
                            # Log error or handle as appropriate
                            print(f"Warning: Could not reconstruct parameter {param_name} for {plugin_id}: {e}")
                            continue # Skip this parameter

            # Ensure all required fields for PluginInfo are present
            try:
                reconstructed_plugins[plugin_id] = PluginInfo(
                    id=plugin_data_dict.get("id", plugin_id), # Use key as fallback for id
                    name=plugin_data_dict.get("name", "Unknown Plugin Name"),
                    path=plugin_data_dict.get("path", ""),
                    filename=plugin_data_dict.get("filename", ""),
                    plugin_type=plugin_data_dict.get("plugin_type", "unknown"),
                    parameters=reconstructed_params,
                    manufacturer=plugin_data_dict.get("manufacturer"),
                    name_in_file=plugin_data_dict.get("name_in_file")
                )
            except TypeError as e: # If required fields are missing
                print(f"Warning: Could not reconstruct plugin info for {plugin_id}: {e}")
                continue # Skip this plugin
        return reconstructed_plugins
    else:
        # For other JSON files (e.g., ignores list), return the raw loaded data
        # The type hint Dict[Any, Any] is broad; specific callers might expect List or Dict[str,X]
        return raw_data

def save_json_file(data: Dict[Any, Any], file_path: Path) -> None: # Or list/Any for data
    """ Save JSON data to a file. """
    ensure_folder(file_path) # Ensures parent directory exists
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

def load_ignores(ignores_path: Path) -> Set[str]:
    """ Load ignores data (list of strings) from the file. """
    content = load_json_file(ignores_path)
    if isinstance(content, list): # Expects a list of strings
        return set(item for item in content if isinstance(item, str))
    return set()

def save_ignores(ignores: Set[str], ignores_path: Path) -> None:
    """ Save ignores data to the file. """
    save_json_file(sorted(list(ignores)), ignores_path)

def copy_default_ignores(destination_path: Path) -> None:
    """ Copy the default ignores file to the destination if it does not exist. """
    try:
        # importlib.resources.files() returns a Traversable object.
        # For a file, .joinpath() with its own name gives a path to it.
        # Then resolve to get an absolute path.
        # 'pedalboard_pluginary.resources' should be where the resources package is.
        # Or, if 'resources' is a sub-package of 'data's package: from . import resources
        # Assuming 'pedalboard_pluginary' is the top-level package for resources.
        import importlib.resources
        default_ignores_src_path = importlib.resources.files('pedalboard_pluginary.resources').joinpath('default_ignores.json')

        if not destination_path.exists():
            ensure_folder(destination_path) # Ensures parent directory exists
            # We need to ensure default_ignores_src_path can be used by shutil.copy
            # If it's a Traversable that represents a file within a zip/egg,
            # shutil.copy might not work directly. We might need to read content and write.
            # However, for typical installations, this should be a file system path.
            with importlib.resources.as_file(default_ignores_src_path) as src_file_on_fs:
                if src_file_on_fs.exists():
                    shutil.copy(src_file_on_fs, destination_path)
                else:
                    # Fallback: create an empty list if source is missing for some reason
                    save_json_file([], destination_path) # Use an empty list for JSON array
    except (ImportError, FileNotFoundError, TypeError) as e: # TypeError for module not a package etc.
        # Fallback if importlib.resources fails (e.g. older python where backport not installed, or unexpected structure)
        # or if the resource is not found.
        print(f"Warning: Could not copy default ignores using importlib.resources: {e}. Attempting pkg_resources or creating empty.")
        try:
            # Try pkg_resources as a fallback if it was working before
            default_ignores_src_path_str_pr: str = resource_filename('pedalboard_pluginary', 'resources/default_ignores.json')
            default_ignores_src_path_pr: Path = Path(default_ignores_src_path_str_pr)
            if not destination_path.exists():
                ensure_folder(destination_path)
                if default_ignores_src_path_pr.exists():
                    shutil.copy(default_ignores_src_path_pr, destination_path)
                else:
                    save_json_file([], destination_path)
        except Exception as e_pr: # Catch all for pkg_resources fallback
            print(f"Warning: pkg_resources fallback for default ignores also failed: {e_pr}. Creating empty ignores file.")
            if not destination_path.exists():
                ensure_folder(destination_path)
                save_json_file([], destination_path)
