import re
import os
import platform
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse
import itertools
import logging
import pedalboard # type: ignore[import-untyped]
# pedalboard might not have complete type stubs.
from tqdm import tqdm # type: ignore[import-untyped]
# tqdm might not have complete type stubs.

from typing import List, Dict, Any, Optional, Set, Union, Type, Pattern
# Union for from_pb_param, Type for plugin_loader classes

from .data import (
    load_json_file,
    save_json_file,
    get_cache_path,
    load_ignores,
    copy_default_ignores,
)
from .utils import ensure_folder, from_pb_param

# Removed basicConfig from here; application/CLI should configure it.
logger: logging.Logger = logging.getLogger(__name__)

from .scanners.au_scanner import AUScanner
from .scanners.vst3_scanner import VST3Scanner
from .models import PluginInfo, PluginParameter, ParameterValue
from .utils import ensure_folder, from_pb_param

# Type alias for Pedalboard plugin classes
PedalboardPluginType = Type[Union[pedalboard.AudioUnitPlugin, pedalboard.VST3Plugin]]


class PedalboardScanner:

    plugins_path: Path
    plugins: Dict[str, PluginInfo] # Updated type
    ignores_path: Path
    ignores: Set[str]
    safe_save: bool
    au_scanner: Optional[AUScanner]
    vst3_scanner: VST3Scanner

    def __init__(self) -> None:
        self.plugins_path = get_cache_path("plugins")
        self.plugins = {}
        self.safe_save = True # If true, saves after each plugin sub-scan
        self.ensure_ignores() # This sets self.ignores

        self.vst3_scanner = VST3Scanner(ignores=self.ignores)
        if platform.system() == "Darwin":
            self.au_scanner = AUScanner(ignores=self.ignores)
        else:
            self.au_scanner = None

    def ensure_ignores(self) -> None:
        self.ignores_path = get_cache_path("ignores")
        if not self.ignores_path.exists():
            copy_default_ignores(self.ignores_path)
        self.ignores = load_ignores(self.ignores_path)

    def save_plugins(self) -> None:
        ensure_folder(self.plugins_path)
        # Sort plugins by key (plugin name) for consistent output

        # Convert PluginInfo objects to dicts for JSON serialization
        from dataclasses import asdict
        plugins_to_save = {k: asdict(v) for k, v in self.plugins.items()}

        sorted_plugins = dict(sorted(plugins_to_save.items()))
        save_json_file(sorted_plugins, self.plugins_path)

    def get_plugin_params(self, plugin_path: Path, plugin_name_in_file: Optional[str]) -> Dict[str, PluginParameter]:
        """
        Loads a plugin and returns its parameters as a dictionary of PluginParameter objects.
        'plugin_name_in_file' is the specific name to load from a multi-plugin file, if any.
        """
        params_data: Dict[str, PluginParameter] = {}
        try:
            plugin_instance = pedalboard.load_plugin(str(plugin_path), plugin_name=plugin_name_in_file)

            for param_id_str, pedalboard_param_obj in plugin_instance.parameters.items():
                # 'param_id_str' is the key like "0", "1", or sometimes string names.
                # 'pedalboard_param_obj' has attributes like 'name', 'label', 'value', 'min_value', 'max_value'.

                # The user-facing name, often in 'label' or 'name' of the parameter object.
                # Fallback to the id_str if others are not present.
                user_facing_name = getattr(pedalboard_param_obj, 'label', None) or \
                                   getattr(pedalboard_param_obj, 'name', param_id_str)

                current_value = from_pb_param(getattr(plugin_instance, param_id_str))

                params_data[user_facing_name] = PluginParameter(
                    name=user_facing_name,
                    value=current_value
                    # TODO: Extend PluginParameter in models.py and here to store:
                    # min_value=getattr(pedalboard_param_obj, 'min_value', None),
                    # max_value=getattr(pedalboard_param_obj, 'max_value', None),
                    # units=getattr(pedalboard_param_obj, 'unit', None)
                    # etc.
                )
            return params_data
        except Exception as e:
            logger.error(f"Could not load/introspect plugin '{plugin_name_in_file or plugin_path.stem}' at '{plugin_path}': {e}")
            return {}


    def scan_single_plugin_file(
        self, plugin_type: str, plugin_path: Path, plugin_loader: PedalboardPluginType
    ) -> None:
        """Scans a single plugin file which might contain multiple plugin definitions."""
        plugin_path_str = str(plugin_path.resolve()) # Use resolved path string
        plugin_filename = plugin_path.name # Full filename, e.g., "MyPlugin.vst3"

        try:
            plugin_names_from_file: List[Optional[str]]
            if hasattr(plugin_loader, 'get_plugin_names_from_file'):
                # This method is expected to return a list of actual plugin names within the file.
                plugin_names_from_file = plugin_loader.get_plugin_names_from_file(plugin_path_str) # type: ignore
            else:
                # Fallback: if the loader doesn't support getting names,
                # assume one plugin per file, and pedalboard will load it by path.
                # Use None to indicate to pedalboard to load the default/only plugin.
                plugin_names_from_file = [None]

            if not plugin_names_from_file:
                logger.warning(f"No plugin names found in file: {plugin_path_str}")
                return

            for name_in_file_to_load in plugin_names_from_file:
                # `name_in_file_to_load` is what `pedalboard.load_plugin(path, plugin_name=name_in_file_to_load)` expects.
                # It can be None if there's only one plugin or loading the default.

                # Attempt to get parameters. This also loads the plugin.
                plugin_parameters = self.get_plugin_params(plugin_path, name_in_file_to_load)

                # Try to get the actual plugin name after loading, if possible.
                # This requires loading the plugin instance again or enhancing get_plugin_params.
                # For now, we construct a display name.
                # The actual loaded plugin's name might be more reliable.
                # Let's load it temporarily to get its actual name and manufacturer (if available)
                # This is inefficient but helps get accurate metadata.
                # TODO: Optimize this by having get_plugin_params return more info or by better use of pedalboard API.
                display_name = name_in_file_to_load or plugin_filename # Default display name
                manufacturer = None
                try:
                    temp_plugin_instance = pedalboard.load_plugin(plugin_path_str, plugin_name=name_in_file_to_load)
                    # Pedalboard plugin instances don't have a standard `.name` or `.manufacturer` attribute accessible this way.
                    # The name is usually what `get_plugin_names_from_file` returns or the filename itself.
                    # Manufacturer info is not directly available from basic pedalboard Plugin objects.
                    # So, we'll use `name_in_file_to_load` or filename as the display name.
                    if name_in_file_to_load:
                        display_name = name_in_file_to_load
                    # else display_name remains plugin_filename
                except Exception:
                    logger.debug(f"Could not load plugin instance for metadata: {plugin_path_str} / {name_in_file_to_load}")


                # Create a unique ID for the plugin entry.
                # This ID is used as the key in the self.plugins dictionary.
                # Format: "type/DisplayName" or "type/Filename(PluginNameInFile)"
                plugin_id_base = name_in_file_to_load if name_in_file_to_load else plugin_filename
                plugin_id = f"{plugin_type}/{plugin_id_base}"

                # If name_in_file_to_load was None (default plugin from file),
                # and plugin_filename was used for plugin_id_base,
                # the display_name should also reflect this if no better name found.
                if not name_in_file_to_load and display_name == plugin_filename:
                     # Attempt to make a cleaner display name if it's like "SineSynth.vst3"
                    display_name = plugin_path.stem


                if plugin_id in self.plugins:
                    logger.debug(f"Plugin with ID {plugin_id} already scanned. Skipping.")
                    continue

                if not plugin_parameters and not name_in_file_to_load:
                    logger.warning(f"Failed to get params for default plugin in {plugin_path_str}. Skipping.")
                    continue

                # If plugin_parameters is empty but it's a named plugin in a file, it might be valid (e.g. no params)
                # We should only skip if it's the default plugin AND params failed.

                plugin_info_entry = PluginInfo(
                    id=plugin_id,
                    name=display_name, # User-facing name
                    path=plugin_path_str,
                    filename=plugin_filename,
                    plugin_type=plugin_type,
                    parameters=plugin_parameters,
                    manufacturer=manufacturer, # Currently always None
                    name_in_file=name_in_file_to_load # Store how it was loaded
                )

                self.plugins[plugin_id] = plugin_info_entry
                logger.debug(f"Scanned and added plugin: {plugin_id}")

        except Exception as e:
            logger.error(f"Error scanning plugin file {plugin_path_str} with loader {plugin_loader.__name__}: {e}")


    def scan_typed_plugins(self, plugin_type: str, found_plugins: List[Path], plugin_loader: PedalboardPluginType) -> None:
        """Scans a list of found plugin files of a specific type."""
        if not found_plugins:
            logger.info(f"No new/found plugins of type {plugin_type} to scan.")
            return

        logger.info(f"Scanning {len(found_plugins)} {plugin_type} plugin files...")
        with tqdm(found_plugins, desc=f"Scanning {plugin_type}", unit="file") as pbar:
            for plugin_path in pbar:
                plugin_fn = plugin_path.stem
                pbar.set_postfix_str(plugin_fn, refresh=True)
                try:
                    self.scan_single_plugin_file(
                        plugin_type, plugin_path, plugin_loader
                    )
                except Exception as e: # Catch-all for safety during iteration
                    logger.error(f"Unexpected error processing {plugin_path}: {e}")

                if self.safe_save: # Save after each file (can be slow)
                    self.save_plugins()
        if not self.safe_save: # Save once at the end if not saving incrementally
            self.save_plugins()


    def scan_aufx_plugins(self, plugin_paths: Optional[List[Path]] = None) -> None:
        """Scans Audio Unit (AUFX) plugins using AUScanner."""
        if not self.au_scanner:
            logger.info("AUScanner not available on this platform.")
            return

        logger.info("Scanning for AUFX plugins...")
        # AUScanner's find_plugin_files takes plugin_paths
        found_aufx_plugin_files = self.au_scanner.find_plugin_files(plugin_paths=plugin_paths)
        self.scan_typed_plugins(
            plugin_type="aufx",
            found_plugins=found_aufx_plugin_files,
            plugin_loader=pedalboard.AudioUnitPlugin,
        )

    def scan_vst3_plugins(self, extra_folders: Optional[List[str]] = None, plugin_paths: Optional[List[Path]] = None) -> None:
        """Scans VST3 plugins using VST3Scanner."""
        logger.info("Scanning for VST3 plugins...")
        # VST3Scanner's find_plugin_files takes extra_folders and plugin_paths
        found_vst3_plugin_files = self.vst3_scanner.find_plugin_files(
            extra_folders=extra_folders, plugin_paths=plugin_paths
        )
        self.scan_typed_plugins(
            plugin_type="vst3",
            found_plugins=found_vst3_plugin_files,
            pedalboard.VST3Plugin,
        )

    def scan_all_plugins(self, extra_folders: Optional[List[str]] = None, plugin_paths: Optional[List[Path]] = None) -> None:
        """Scans all supported plugin types."""
        # If specific plugin_paths are given, we might only scan those.
        # Current logic: if plugin_paths is provided, it's used by type-specific finders.
        # extra_folders is only for VST3 if plugin_paths is None for VST3.

        self.scan_vst3_plugins(extra_folders=extra_folders, plugin_paths=plugin_paths)
        if platform.system() == "Darwin":
            self.scan_aufx_plugins(plugin_paths=plugin_paths) # AU only on Darwin

    def full_scan(self, extra_folders: Optional[List[str]] = None) -> None:
        """Performs a full scan, clearing existing plugins."""
        logger.info("Starting full plugin scan (clearing existing cache)...")
        self.plugins = {} # Clear existing plugins before scan
        # The original 'scan' called scan_plugins with extra_folders=None, which was a bug
        # if extra_folders was meant to be passed down.
        # Assuming 'scan_all_plugins' is the intended method for a general scan.
        self.scan_all_plugins(extra_folders=extra_folders) # plugin_paths=None for discovery
        self.save_plugins()
        logger.info("Full plugin scan finished.")

    def rescan(self, extra_folders: Optional[List[str]] = None) -> None: # Kept original name
        """Alias for full_scan for backward compatibility or semantic preference."""
        self.full_scan(extra_folders=extra_folders)

    def update_scan(self, extra_folders: Optional[List[str]] = None) -> None:
        """Scans for new plugins not already in the cache."""
        logger.info("Starting update scan (looking for new plugins)...")
        if not self.plugins_path.exists():
            logger.info("No existing plugin cache found. Performing full scan instead.")
            self.full_scan(extra_folders=extra_folders)
            return

        # Load existing plugins to compare against
        # Type annotation for p ensures mypy knows p is a dict and has 'path' and 'type'
        existing_plugins_data = load_json_file(self.plugins_path)
        if not isinstance(existing_plugins_data, dict): # Should be a dict
             logger.warning("Plugin cache is not a valid dictionary. Performing full scan.")
             self.full_scan(extra_folders=extra_folders)
             return

        self.plugins = existing_plugins_data # Start with current cache

        # Logic to find only new plugins
        # VST3
        all_found_vst3_paths: Set[Path] = {p.resolve() for p in self._find_vst3_plugins(extra_folders=extra_folders)}
        cached_vst3_paths: Set[Path] = {Path(p_info["path"]).resolve() for p_info in self.plugins.values() if p_info.get("type") == "vst3" and "path" in p_info}
        new_vst3_paths_to_scan: List[Path] = sorted(list(all_found_vst3_paths - cached_vst3_paths))
        if new_vst3_paths_to_scan:
            logger.info(f"Found {len(new_vst3_paths_to_scan)} new VST3 plugin files to scan.")
            self.scan_vst3_plugins(plugin_paths=new_vst3_paths_to_scan) # Scan only these new paths
        else:
            logger.info("No new VST3 plugin files found.")

        # AUFX (macOS only)
        if platform.system() == "Darwin":
            all_found_aufx_paths: Set[Path] = {p.resolve() for p in self._find_aufx_plugins()}
            cached_aufx_paths: Set[Path] = {Path(p_info["path"]).resolve() for p_info in self.plugins.values() if p_info.get("type") == "aufx" and "path" in p_info}
            new_aufx_paths_to_scan: List[Path] = sorted(list(all_found_aufx_paths - cached_aufx_paths))
            if new_aufx_paths_to_scan:
                logger.info(f"Found {len(new_aufx_paths_to_scan)} new AUFX plugin files to scan.")
                self.scan_aufx_plugins(plugin_paths=new_aufx_paths_to_scan) # Scan only these
            else:
                logger.info("No new AUFX plugin files found.")

        # self.save_plugins() is called within scan_typed_plugins if not safe_save,
        # or after each file if safe_save. If scan_typed_plugins wasn't called (no new plugins),
        # an explicit save here might be redundant but harmless if state hasn't changed.
        # However, if safe_save is False, it's crucial here.
        if not self.safe_save and (new_vst3_paths_to_scan or (platform.system() == "Darwin" and 'new_aufx_paths_to_scan' in locals() and new_aufx_paths_to_scan)):
             self.save_plugins()
        elif not new_vst3_paths_to_scan and not (platform.system() == "Darwin" and 'new_aufx_paths_to_scan' in locals() and new_aufx_paths_to_scan):
             logger.info("No new plugins found in update scan. Cache remains unchanged.")


        logger.info("Update scan finished.")

    # Renamed original 'scan' to 'full_scan' and 'update' to 'update_scan' for clarity.
    # Kept original names for CLI compatibility by aliasing them if needed in __main__.py
    # For direct class usage, the new names are more descriptive.
    # The original `scan` method in the class was equivalent to `full_scan`.
    # The original `update` method in the class is `update_scan`.
    # The CLI part in __main__.py used `rescan` (for full) and `update`.

    def get_json(self) -> str:
        """Returns a JSON string representation of the currently scanned/loaded plugins."""
        return json.dumps(self.plugins, indent=4)
