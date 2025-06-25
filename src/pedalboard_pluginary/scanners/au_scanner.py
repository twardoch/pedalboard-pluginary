"""
Handles scanning of Audio Unit (AU) plugins on macOS.
"""

import logging
import platform
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import unquote, urlparse

import pedalboard  # type: ignore[import-untyped]

from ..models import PluginInfo, PluginParameter
from ..utils import from_pb_param

logger = logging.getLogger(__name__)


class AUScanner:
    """Scanner for Audio Unit plugins."""

    def __init__(
        self,
        ignore_paths: Optional[List[str]] = None,
        specific_paths: Optional[List[str]] = None,
    ):
        """Initialize the AU scanner with optional ignore paths and specific paths."""
        self.ignore_paths = ignore_paths or []
        self.specific_paths = specific_paths or []
        self._platform_check()

    def _platform_check(self) -> None:
        """Check if running on macOS."""
        if platform.system() != "Darwin":
            logger.info("AU scanning is only applicable on macOS.")
            return

    def _list_aufx_plugins_raw(self) -> List[str]:
        """List all Audio Unit effects plugins using auval."""
        try:
            result = subprocess.run(
                ["auval", "-a"], capture_output=True, text=True, check=True
            )
            return result.stdout.splitlines()
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Failed to run auval command.")
            return []

    def _parse_aufx_path_from_auval(self, plugin_str: str) -> Optional[Path]:
        """Parse the AU plugin path from auval output."""
        parts = plugin_str.strip().split()
        if len(parts) >= 3 and parts[0] == "aufx":
            bundle_id = parts[2]
            
            # Common AU plugin locations
            locations = [
                Path("/Library/Audio/Plug-Ins/Components"),
                Path("~/Library/Audio/Plug-Ins/Components").expanduser(),
                Path("/System/Library/Components"),
            ]
            
            for location in locations:
                if location.exists():
                    for component in location.glob("*.component"):
                        if bundle_id in str(component):
                            return component
            
            # Try to find by exact name match
            for location in locations:
                if location.exists():
                    component_path = location / f"{bundle_id}.component"
                    if component_path.exists():
                        return component_path
        
        return None

    def find_plugin_files(self, plugin_paths: Optional[List[Path]] = None) -> List[Path]:
        """Find all AU plugin files."""
        if platform.system() != "Darwin":
            return []

        if plugin_paths:
            # Filter specific paths to only AU component files
            return [p for p in plugin_paths if p.suffix == ".component" and p.exists()]

        discovered_plugins = []
        auval_output = self._list_aufx_plugins_raw()
        
        for line in auval_output:
            if line.strip().startswith("aufx"):
                plugin_path = self._parse_aufx_path_from_auval(line)
                if plugin_path and self._should_include_path(plugin_path):
                    discovered_plugins.append(plugin_path)

        logger.info(f"Found {len(discovered_plugins)} AU plugins to consider.")
        return discovered_plugins

    def scan_plugin(self, plugin_path: Path) -> Optional[PluginInfo]:
        """Scan an AU plugin and return its information."""
        if not plugin_path.exists() or plugin_path.suffix != ".component":
            return None

        try:
            # Try to load the plugin using pedalboard
            plugin = pedalboard.load_plugin(str(plugin_path))  # type: ignore[attr-defined]
            
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
            display_name = plugin_path.stem
            if hasattr(plugin, 'name'):
                display_name = str(plugin.name)
            
            return PluginInfo(
                id=f"aufx/{plugin_path.stem}",
                name=display_name,
                path=str(plugin_path),
                filename=plugin_path.name,
                plugin_type="aufx",
                parameters=params,
                manufacturer=manufacturer,
            )

        except Exception as e:
            logger.error(f"Failed to scan AU plugin {plugin_path}: {e}")
            # Fall back to basic info extraction from auval
            try:
                result = subprocess.run(
                    ["auval", "-v", str(plugin_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                
                # Parse basic info from auval output
                name = plugin_path.stem
                manufacturer = None
                
                for line in result.stdout.splitlines():
                    if "NAME:" in line:
                        name = line.split("NAME:", 1)[1].strip()
                    elif "MANUFACTURER:" in line:
                        manufacturer = line.split("MANUFACTURER:", 1)[1].strip()
                
                if name:
                    return PluginInfo(
                        id=f"aufx/{plugin_path.stem}",
                        name=name,
                        path=str(plugin_path),
                        filename=plugin_path.name,
                        plugin_type="aufx",
                        manufacturer=manufacturer,
                    )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return None

    def _should_include_path(self, bundle_path: Path) -> bool:
        """Determine if a bundle path should be included based on ignore and specific paths."""
        return not any(
            re.match(pattern, str(bundle_path)) for pattern in self.ignore_paths
        ) and (not self.specific_paths or bundle_path in self.specific_paths)