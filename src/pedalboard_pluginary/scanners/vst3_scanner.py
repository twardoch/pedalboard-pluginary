"""
Handles scanning of VST3 plugins.
"""

import itertools
import logging
import os
import platform
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pedalboard  # type: ignore[import-untyped]

from ..models import PluginInfo, PluginParameter
from ..utils import from_pb_param

logger = logging.getLogger(__name__)


class VST3Scanner:
    """Scans VST3 plugins."""

    def __init__(
        self,
        ignore_paths: Optional[List[str]] = None,
        specific_paths: Optional[List[str]] = None,
    ):
        """Initialize the VST3 scanner with optional ignore paths and specific paths."""
        self.ignore_paths = ignore_paths or []
        self.specific_paths = specific_paths or []

    def _get_default_vst3_folders(self) -> List[Path]:
        """Gets standard VST3 plugin folders for the current OS."""
        os_name: str = platform.system()
        folders: List[Path] = []

        program_files = os.getenv("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.getenv("ProgramFiles(x86)", "C:\\Program Files (x86)")

        if os_name == "Windows":
            folders = [
                Path(program_files) / "Common Files" / "VST3",
                Path(program_files_x86) / "Common Files" / "VST3",
            ]
        elif os_name == "Darwin":  # macOS
            folders = [
                Path("~/Library/Audio/Plug-Ins/VST3").expanduser(),
                Path("/Library/Audio/Plug-Ins/VST3"),
            ]
        elif os_name == "Linux":
            # Standard VST3 paths on Linux
            # See: https://steinbergmedia.github.io/vst3_dev_portal/pages/Technical+Documentation/Locations+Format/Plugin+Locations.html
            folders = [
                Path("~/.vst3").expanduser(),  # User specific
                Path("/usr/lib/vst3"),  # System wide
                Path("/usr/local/lib/vst3"),  # Locally installed system wide
            ]

        return [f for f in folders if f.exists()]

    def find_plugin_files(
        self,
        extra_folders: Optional[List[str]] = None,
        plugin_paths: Optional[List[Path]] = None,
    ) -> List[Path]:
        """Find all VST3 plugin files in standard and custom folders."""
        plugin_type = "vst3"

        all_folders_to_search: List[Path] = self._get_default_vst3_folders()
        
        if extra_folders:
            all_folders_to_search.extend([Path(folder) for folder in extra_folders])
        
        if plugin_paths:
            # Filter specific paths to only VST3 files
            return [p for p in plugin_paths if p.suffix == ".vst3" and p.exists()]

        if not all_folders_to_search:
            logger.warning("No VST3 folders to search.")
            return []

        logger.info(f"Searching for VST3 plugins in: {all_folders_to_search}")

        # Using set to avoid adding same path multiple times if folders overlap or symlinked
        discovered_plugin_path_set = set()
        for folder in all_folders_to_search:
            for item in folder.glob(f"*.{plugin_type}"):
                if item.is_file() and self._should_include_path(item):
                    discovered_plugin_path_set.add(item.resolve())

        vst3_plugin_files = sorted(list(discovered_plugin_path_set))
        logger.info(f"Found {len(vst3_plugin_files)} VST3 plugin files to consider.")
        return vst3_plugin_files

    def scan_plugin(self, plugin_path: Path) -> Optional[PluginInfo]:
        """Scan a VST3 plugin and return its information."""
        if not plugin_path.exists() or plugin_path.suffix != ".vst3":
            return None

        try:
            # Load the plugin to get its parameters
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
            
            # Try to get manufacturer info if available
            manufacturer = None
            if hasattr(plugin, 'manufacturer'):
                manufacturer = str(plugin.manufacturer)
            
            # Get the plugin's display name if available
            display_name = plugin_path.stem
            if hasattr(plugin, 'name'):
                display_name = str(plugin.name)
            
            return PluginInfo(
                id=f"vst3/{plugin_path.stem}",
                name=display_name,
                path=str(plugin_path),
                filename=plugin_path.name,
                plugin_type="vst3",
                parameters=params,
                manufacturer=manufacturer,
            )
        except Exception as e:
            logger.error(f"Error scanning VST3 plugin {plugin_path}: {e}")
            return None

    def _should_include_path(self, plugin_path: Path) -> bool:
        """Determine if a plugin path should be included based on ignore and specific paths."""
        return not any(
            re.match(pattern, str(plugin_path)) for pattern in self.ignore_paths
        ) and (not self.specific_paths or plugin_path in self.specific_paths)