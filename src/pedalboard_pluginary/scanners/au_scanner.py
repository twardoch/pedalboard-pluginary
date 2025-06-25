"""
Handles scanning of Audio Unit (AU) plugins on macOS.
"""

import logging
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import pedalboard  # type: ignore[import-untyped]

from ..base_scanner import BaseScanner
from ..constants import AU_EXTENSION, PLATFORM_MACOS, PLUGIN_TYPE_AU
from ..exceptions import PlatformError, PluginLoadError, PluginScanError
from ..models import PluginInfo, PluginParameter
from ..utils import from_pb_param

logger = logging.getLogger(__name__)


class AUScanner(BaseScanner):
    """Scanner for Audio Unit plugins."""
    
    def __init__(
        self,
        ignore_paths: Optional[List[str]] = None,
        specific_paths: Optional[List[str]] = None,
    ):
        """Initialize the AU scanner with optional ignore paths and specific paths."""
        super().__init__(ignore_paths, specific_paths)
        self._is_macos = platform.system() == PLATFORM_MACOS
        if not self._is_macos:
            logger.info("AU scanning is only available on macOS.")
    
    @property
    def plugin_type(self) -> str:
        """Return the plugin type this scanner handles."""
        return PLUGIN_TYPE_AU
    
    @property
    def supported_extensions(self) -> List[str]:
        """Return list of file extensions this scanner supports."""
        return [AU_EXTENSION]
    
    def _get_au_plugin_locations(self) -> List[Path]:
        """Get standard AU plugin locations on macOS."""
        return [
            Path("/Library/Audio/Plug-Ins/Components"),
            Path("~/Library/Audio/Plug-Ins/Components").expanduser(),
            Path("/System/Library/Components"),
        ]
    
    def _list_aufx_plugins_raw(self) -> List[str]:
        """List all Audio Unit effects plugins using auval."""
        if not self._is_macos:
            return []
        
        try:
            result = subprocess.run(
                ["auval", "-a"], 
                capture_output=True, 
                text=True, 
                check=True,
                timeout=30
            )
            return result.stdout.splitlines()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to run auval command: {e}")
            return []
    
    def _parse_aufx_path_from_auval(self, plugin_str: str) -> Optional[Path]:
        """Parse the AU plugin path from auval output."""
        parts = plugin_str.strip().split()
        if len(parts) >= 3 and parts[0] == "aufx":
            bundle_id = parts[2]
            
            # Search in standard locations
            for location in self._get_au_plugin_locations():
                if location.exists():
                    # First try exact match
                    component_path = location / f"{bundle_id}.component"
                    if component_path.exists():
                        return component_path
                    
                    # Then search for partial match
                    for component in location.glob("*.component"):
                        if bundle_id in str(component):
                            return component
        
        return None
    
    def find_plugin_files(self, paths: Optional[List[Path]] = None) -> List[Path]:
        """Find all AU plugin files.
        
        Args:
            paths: Optional list of specific paths to check.
            
        Returns:
            List of paths to AU plugin files found.
        """
        if not self._is_macos:
            return []
        
        if paths:
            # Filter specific paths to only AU component files
            au_paths = [p for p in paths if p.suffix in self.supported_extensions]
            return self._filter_plugin_paths(au_paths)
        
        # Use auval to discover plugins
        discovered_plugins = []
        auval_output = self._list_aufx_plugins_raw()
        
        for line in auval_output:
            if line.strip().startswith("aufx"):
                plugin_path = self._parse_aufx_path_from_auval(line)
                if plugin_path:
                    discovered_plugins.append(plugin_path)
        
        # Also scan standard directories for any missed plugins
        for location in self._get_au_plugin_locations():
            if location.exists():
                try:
                    for component in location.glob("*.component"):
                        if component not in discovered_plugins:
                            discovered_plugins.append(component)
                except Exception as e:
                    logger.error(f"Error scanning directory {location}: {e}")
        
        # Apply filtering
        filtered_list = self._filter_plugin_paths(discovered_plugins)
        logger.info(f"Found {len(filtered_list)} AU plugins after filtering.")
        return filtered_list
    
    def scan_plugin(self, path: Path) -> Optional[PluginInfo]:
        """Scan an AU plugin and return its information.
        
        Args:
            path: Path to the AU plugin file.
            
        Returns:
            PluginInfo object if successful, None if scanning failed.
        """
        if not self.validate_plugin_path(path):
            logger.warning(f"Invalid plugin path: {path}")
            return None
        
        try:
            # Try to load the plugin using pedalboard
            logger.debug(f"Loading AU plugin: {path}")
            plugin = pedalboard.load_plugin(str(path))  # type: ignore[attr-defined]
            
            # Extract parameters
            params: Dict[str, PluginParameter] = {}
            if hasattr(plugin, 'parameters'):
                for param_name, param_value in plugin.parameters.items():
                    # Convert the parameter value to our expected type
                    converted_value = from_pb_param(param_value)
                    params[param_name] = PluginParameter(
                        name=param_name,
                        value=converted_value,
                    )
            
            # Try to get manufacturer info
            manufacturer = None
            if hasattr(plugin, 'manufacturer'):
                manufacturer = str(plugin.manufacturer)
            
            # Get the plugin's display name
            display_name = path.stem
            if hasattr(plugin, 'name'):
                display_name = str(plugin.name)
            
            plugin_info = PluginInfo(
                id=self._create_plugin_id(path),
                name=display_name,
                path=str(path),
                filename=path.name,
                plugin_type=self.plugin_type,
                parameters=params,
                manufacturer=manufacturer,
            )
            
            logger.info(f"Successfully scanned AU plugin: {display_name}")
            return plugin_info
            
        except PluginLoadError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to scan AU plugin {path} with pedalboard: {e}")
            # Fall back to basic info extraction from auval
            return self._scan_with_auval(path)
    
    def _scan_with_auval(self, path: Path) -> Optional[PluginInfo]:
        """Scan plugin using auval as fallback method."""
        try:
            result = subprocess.run(
                ["auval", "-v", str(path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            # Parse basic info from auval output
            name = path.stem
            manufacturer = None
            
            for line in result.stdout.splitlines():
                if "NAME:" in line:
                    name = line.split("NAME:", 1)[1].strip()
                elif "MANUFACTURER:" in line:
                    manufacturer = line.split("MANUFACTURER:", 1)[1].strip()
            
            if name:
                plugin_info = PluginInfo(
                    id=self._create_plugin_id(path),
                    name=name,
                    path=str(path),
                    filename=path.name,
                    plugin_type=self.plugin_type,
                    manufacturer=manufacturer,
                    parameters={},  # No parameters from auval
                )
                logger.info(f"Scanned AU plugin with auval: {name}")
                return plugin_info
                
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Failed to scan {path} with auval: {e}")
        
        return None