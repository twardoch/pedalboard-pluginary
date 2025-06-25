import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pedalboard  # type: ignore[import-untyped]
from tqdm import tqdm  # type: ignore[import-untyped]

from .data import (
    copy_default_ignores,
    get_cache_path,
    load_ignores,
    load_json_file,
    save_json_file,
)
from .models import ParameterValue, PluginInfo, PluginParameter
from .scanners.au_scanner import AUScanner
from .scanners.vst3_scanner import VST3Scanner
from .utils import ensure_folder, from_pb_param

logger: logging.Logger = logging.getLogger(__name__)


class PedalboardScanner:
    """Main scanner class that coordinates scanning of all plugin types."""

    def __init__(
        self,
        ignore_paths: Optional[List[str]] = None,
        specific_paths: Optional[List[str]] = None,
    ):
        """Initialize the scanner with optional ignore paths and specific paths."""
        self.ignore_paths = ignore_paths or []
        self.specific_paths = specific_paths or []
        self.plugins: Dict[str, PluginInfo] = {}
        self.plugins_path = get_cache_path("plugins")
        self.ignores_path = get_cache_path("ignores")
        
        # Initialize ignores
        copy_default_ignores(self.ignores_path)
        self.ignores = load_ignores(self.ignores_path)
        
        # Initialize scanners
        self.scanners = [
            AUScanner(
                ignore_paths=self.ignore_paths, specific_paths=self.specific_paths
            ),
            VST3Scanner(
                ignore_paths=self.ignore_paths, specific_paths=self.specific_paths
            ),
        ]
        
        # Load existing plugin data if available
        self.load_data()

    def load_data(self) -> None:
        """Load existing plugin data from cache."""
        if self.plugins_path.exists():
            loaded_data = load_json_file(self.plugins_path)
            if isinstance(loaded_data, dict):
                # Convert loaded data to PluginInfo objects
                for key, plugin_data in loaded_data.items():
                    if isinstance(plugin_data, dict):
                        # Convert parameters
                        params = {}
                        if "parameters" in plugin_data:
                            for param_name, param_data in plugin_data["parameters"].items():
                                if isinstance(param_data, dict):
                                    params[param_name] = PluginParameter(
                                        name=param_data.get("name", param_name),
                                        value=param_data.get("value"),
                                    )
                        
                        self.plugins[key] = PluginInfo(
                            id=plugin_data.get("id", key),
                            name=plugin_data.get("name", ""),
                            path=plugin_data.get("path", ""),
                            filename=plugin_data.get("filename", ""),
                            plugin_type=plugin_data.get("plugin_type", ""),
                            parameters=params,
                            manufacturer=plugin_data.get("manufacturer"),
                            name_in_file=plugin_data.get("name_in_file"),
                        )

    def save_data(self) -> None:
        """Save plugin data to cache."""
        ensure_folder(self.plugins_path.parent)
        
        # Convert PluginInfo objects to dictionaries for JSON serialization
        plugins_dict = {}
        for key, plugin_info in self.plugins.items():
            plugin_dict = {
                "id": plugin_info.id,
                "name": plugin_info.name,
                "path": plugin_info.path,
                "filename": plugin_info.filename,
                "plugin_type": plugin_info.plugin_type,
                "parameters": {},
                "manufacturer": plugin_info.manufacturer,
                "name_in_file": plugin_info.name_in_file,
            }
            
            # Convert parameters
            for param_name, param in plugin_info.parameters.items():
                plugin_dict["parameters"][param_name] = {
                    "name": param.name,
                    "value": param.value,
                }
            
            plugins_dict[key] = plugin_dict
        
        save_json_file(plugins_dict, self.plugins_path)
        
        # Save updated ignores
        save_json_file(list(self.ignores), self.ignores_path)

    def full_scan(self) -> Dict[str, PluginInfo]:
        """Perform a full scan of all plugin types."""
        self.plugins = {}
        total_files = 0
        
        # First, count all plugin files
        all_plugin_files = []
        for scanner in self.scanners:
            plugin_files = scanner.find_plugin_files()
            all_plugin_files.extend([(scanner, pf) for pf in plugin_files])
            total_files += len(plugin_files)
        
        # Scan all plugins with progress bar
        with tqdm(total=total_files, desc="Scanning plugins") as pbar:
            for scanner, plugin_file in all_plugin_files:
                plugin_key = f"{scanner.__class__.__name__.replace('Scanner', '').lower()}:{plugin_file}"
                
                # Skip ignored plugins
                if plugin_key in self.ignores:
                    logger.info(f"Skipping ignored plugin: {plugin_file}")
                    pbar.update(1)
                    continue
                
                try:
                    plugin_info = scanner.scan_plugin(plugin_file)
                    if plugin_info:
                        self.plugins[plugin_info.id] = plugin_info
                        logger.info(f"Scanned plugin: {plugin_file}")
                except Exception as e:
                    logger.error(f"Failed to scan plugin {plugin_file}: {e}")
                    self.ignores.add(plugin_key)
                
                pbar.update(1)
        
        # Save the results
        self.save_data()
        return self.plugins

    def update_scan(self) -> Dict[str, PluginInfo]:
        """Update the scan with new plugins while preserving existing data."""
        # Keep track of existing plugins
        existing_plugins = set(self.plugins.keys())
        new_plugins = {}
        
        # Find all plugin files
        all_plugin_files = []
        for scanner in self.scanners:
            plugin_files = scanner.find_plugin_files()
            all_plugin_files.extend([(scanner, pf) for pf in plugin_files])
        
        # Only scan plugins that aren't already in the cache
        plugins_to_scan = []
        for scanner, plugin_file in all_plugin_files:
            plugin_type = scanner.__class__.__name__.replace('Scanner', '').lower()
            plugin_key = f"{plugin_type}:{plugin_file}"
            
            if plugin_key not in existing_plugins and plugin_key not in self.ignores:
                plugins_to_scan.append((scanner, plugin_file, plugin_key))
        
        # Scan new plugins with progress bar
        if plugins_to_scan:
            with tqdm(total=len(plugins_to_scan), desc="Scanning new plugins") as pbar:
                for scanner, plugin_file, plugin_key in plugins_to_scan:
                    try:
                        plugin_info = scanner.scan_plugin(plugin_file)
                        if plugin_info:
                            self.plugins[plugin_info.id] = plugin_info
                            new_plugins[plugin_info.id] = plugin_info
                            logger.info(f"Scanned new plugin: {plugin_file}")
                    except Exception as e:
                        logger.error(f"Failed to scan plugin {plugin_file}: {e}")
                        self.ignores.add(plugin_key)
                    
                    pbar.update(1)
            
            # Save updated data
            self.save_data()
        
        return new_plugins

    def get_json(self) -> str:
        """Return the plugins data as a JSON string."""
        # Convert to serializable format
        plugins_dict = {}
        for key, plugin_info in self.plugins.items():
            plugin_dict = {
                "id": plugin_info.id,
                "name": plugin_info.name,
                "path": plugin_info.path,
                "filename": plugin_info.filename,
                "plugin_type": plugin_info.plugin_type,
                "parameters": {},
                "manufacturer": plugin_info.manufacturer,
                "name_in_file": plugin_info.name_in_file,
            }
            
            # Convert parameters
            for param_name, param in plugin_info.parameters.items():
                plugin_dict["parameters"][param_name] = {
                    "name": param.name,
                    "value": param.value,
                }
            
            plugins_dict[key] = plugin_dict
        
        return json.dumps(plugins_dict, indent=2)