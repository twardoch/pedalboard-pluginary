"""
Handles scanning of VST3 plugins.
"""

import logging
import os
import platform
from pathlib import Path
from typing import Dict, List, Optional

import pedalboard

from ..async_scanner import AsyncScannerMixin
from ..base_scanner import BaseScanner
from ..constants import PLUGIN_TYPE_VST3, VST3_EXTENSION, PLUGIN_LOAD_TIMEOUT
from ..exceptions import PluginLoadError, PluginScanError
from ..models import PluginInfo, PluginParameter
from ..timeout import sync_timeout, TimeoutError
from ..utils import from_pb_param

logger = logging.getLogger(__name__)


class VST3Scanner(BaseScanner, AsyncScannerMixin):
    """Scanner for VST3 plugins."""
    
    @property
    def plugin_type(self) -> str:
        """Return the plugin type this scanner handles."""
        return PLUGIN_TYPE_VST3
    
    @property
    def supported_extensions(self) -> List[str]:
        """Return list of file extensions this scanner supports."""
        return [VST3_EXTENSION]
    
    def _get_default_vst3_folders(self) -> List[Path]:
        """Get standard VST3 plugin folders for the current OS."""
        os_name = platform.system()
        folders: List[Path] = []
        
        if os_name == "Windows":
            program_files = os.getenv("ProgramFiles", "C:\\Program Files")
            program_files_x86 = os.getenv("ProgramFiles(x86)", "C:\\Program Files (x86)")
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
            folders = [
                Path("~/.vst3").expanduser(),
                Path("/usr/lib/vst3"),
                Path("/usr/local/lib/vst3"),
            ]
        
        return [f for f in folders if f.exists()]
    
    def find_plugin_files(self, paths: Optional[List[Path]] = None) -> List[Path]:
        """Find all VST3 plugin files in standard and custom folders.
        
        Args:
            paths: Optional list of specific paths to check.
            
        Returns:
            List of paths to VST3 plugin files found.
        """
        if paths:
            # Filter specific paths to only VST3 files
            vst3_paths = [p for p in paths if p.suffix in self.supported_extensions]
            return self._filter_plugin_paths(vst3_paths)
        
        # Search default VST3 folders
        search_folders = self._get_default_vst3_folders()
        
        if not search_folders:
            logger.warning("No VST3 folders to search.")
            return []
        
        logger.info(f"Searching for VST3 plugins in: {search_folders}")
        
        # Find all VST3 files
        discovered_plugins = set()
        for folder in search_folders:
            try:
                for vst3_file in folder.glob("*.vst3"):
                    if vst3_file.is_file():
                        discovered_plugins.add(vst3_file.resolve())
            except Exception as e:
                logger.error(f"Error searching folder {folder}: {e}")
        
        # Apply filtering
        plugin_list = sorted(list(discovered_plugins))
        filtered_list = self._filter_plugin_paths(plugin_list)
        
        logger.info(f"Found {len(filtered_list)} VST3 plugins after filtering.")
        return filtered_list
    
    def scan_plugin(self, path: Path) -> Optional[PluginInfo]:
        """Scan a VST3 plugin and return its information.
        
        Args:
            path: Path to the VST3 plugin file.
            
        Returns:
            PluginInfo object if successful, None if scanning failed.
        """
        if not self.validate_plugin_path(path):
            logger.warning(f"Invalid plugin path: {path}")
            return None
        
        try:
            # Load the plugin to get its parameters with timeout
            logger.debug(f"Loading VST3 plugin: {path}")
            plugin = sync_timeout(pedalboard.load_plugin, PLUGIN_LOAD_TIMEOUT, str(path))
            
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
            
            logger.info(f"Successfully scanned VST3 plugin: {display_name}")
            return plugin_info
            
        except TimeoutError as e:
            logger.warning(f"VST3 plugin {path} timed out during loading: {e}")
            raise PluginLoadError(
                plugin_path=str(path),
                reason=f"Plugin loading timed out after {e.timeout}s"
            )
        except PluginLoadError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error(f"Error scanning VST3 plugin {path}: {e}")
            raise PluginScanError(
                plugin_path=str(path),
                scanner_type=self.plugin_type,
                reason=str(e)
            )