# pedalboard_pluginary/scanners/au_scanner.py
"""
Handles scanning of Audio Unit (AU) plugins on macOS.
"""
import logging
import platform
import re
import subprocess
from pathlib import Path
from typing import List, Set, Optional, Any, Dict
from urllib.parse import unquote, urlparse

# Assuming models.py will be created with PluginInfo, PluginParameter
# from ..models import PluginInfo, PluginParameter
# For now, using Dict[str, Any] as placeholder
PluginDict = Dict[str, Any]
ParamDict = Dict[str, Any] # Replace Any with Union[float, bool, str] later

logger = logging.getLogger(__name__)

class AUScanner:
    """Scans Audio Unit (AU) plugins on macOS."""

    RE_AUFX: re.Pattern[str] = re.compile(
        r"aufx\s+(\w+)\s+(\w+)\s+-\s+(.*?):\s+(.*?)\s+\((.*?)\)"
    )

    def __init__(self, ignores: Set[str]):
        self.ignores = ignores
        # self.plugins: Dict[str, PluginInfo] = {} # To be used with typed models

    def _list_aufx_plugins_raw(self) -> List[str]:
        """Lists Audio Unit plugins using auval. Returns list of lines from auval output."""
        if platform.system() != "Darwin":
            logger.info("AU scanning is only applicable on macOS.")
            return []
        try:
            result = subprocess.run(
                ["auval", "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=True,
            )
            return result.stdout.splitlines()
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Error running auval (is it installed and in PATH?): {e}")
            return []

    def find_plugin_files(self, plugin_paths: Optional[List[Path]] = None) -> List[Path]:
        """
        Finds resolvable paths to AUFX plugins from auval output, respecting ignores.
        If plugin_paths is provided, filters the auval results to those paths.
        """
        if platform.system() != "Darwin":
            return []

        aufx_plugin_files: List[Path] = []
        plugin_type: str = "aufx"

        resolved_user_plugin_paths: Optional[List[Path]] = None
        if plugin_paths:
            resolved_user_plugin_paths = [p.resolve() for p in plugin_paths]

        for line in self._list_aufx_plugins_raw():
            match = self.RE_AUFX.match(line)
            if match:
                (
                    _plugin_code,
                    _vendor_code,
                    _vendor_name,
                    _plugin_name, # This is the plugin name, not the filename
                    plugin_url,
                ) = match.groups()

                try:
                    parsed_url = urlparse(plugin_url)
                    plugin_path_str = unquote(parsed_url.path)
                    if not plugin_path_str:
                        logger.warning(f"Empty path from AUFX plugin URL: {plugin_url}")
                        continue

                    # Some paths from auval might be like '/path/to/MyPlugin.component/Contents/MacOS/MyPlugin'
                    # We are interested in the '.component' bundle path.
                    # A common pattern is that the actual binary is inside .component/Contents/MacOS/
                    # Pedalboard typically expects the path to the bundle itself.
                    potential_path = Path(plugin_path_str)

                    # Try to find the .component or .bundle parent
                    bundle_path: Optional[Path] = None
                    current_path_check = potential_path
                    while current_path_check != current_path_check.parent: # Stop at root
                        if current_path_check.suffix in [".component", ".au", ".bundle"]: # .au is less common but possible
                            bundle_path = current_path_check
                            break
                        current_path_check = current_path_check.parent

                    if not bundle_path:
                        logger.warning(f"Could not determine bundle path for AUFX plugin at {plugin_path_str} (URL: {plugin_url}). Using direct path.")
                        # If we can't find a bundle, pedalboard might still load it, or it might be an issue.
                        # This path might point directly to an executable or a resource.
                        # For now, we'll use the resolved path from the URL.
                        # This behavior needs testing with various AU plugins.
                        bundle_path = potential_path.resolve()
                    else:
                        bundle_path = bundle_path.resolve()

                except Exception as e:
                    logger.warning(f"Could not parse/resolve AUFX plugin URL '{plugin_url}': {e}")
                    continue

                plugin_fn_stem: str = bundle_path.stem # e.g., "MyPlugin" from "MyPlugin.component"
                plugin_key: str = f"{plugin_type}/{plugin_fn_stem}" # Key for ignore list

                if plugin_key in self.ignores:
                    logger.debug(f"Ignoring AU plugin {plugin_key} based on ignores list.")
                    continue

                if resolved_user_plugin_paths and bundle_path not in resolved_user_plugin_paths:
                    logger.debug(f"Skipping AU plugin {bundle_path} not in user-provided list.")
                    continue

                if bundle_path not in aufx_plugin_files: # Avoid duplicates
                    aufx_plugin_files.append(bundle_path)

        logger.info(f"Found {len(aufx_plugin_files)} AU plugin files to consider.")
        return aufx_plugin_files

    # Further methods for scanning these files (get_plugin_params, etc.) will be added
    # when integrating with the main PedalboardScanner and models.
    # For now, this class focuses on discovery.

if __name__ == "__main__":
    # Example Usage (macOS only)
    if platform.system() == "Darwin":
        logging.basicConfig(level=logging.DEBUG)
        # Dummy ignores for testing
        test_ignores: Set[str] = {"aufx/DLSMusicDevice", "aufx/SomeOtherPluginToIgnore"}

        scanner = AUScanner(ignores=test_ignores)

        print("--- Finding all AU plugins ---")
        all_au_plugins = scanner.find_plugin_files()
        for p_path in all_au_plugins:
            print(p_path)

        # Example with specific paths (if you knew some paths to filter by)
        # print("\n--- Finding specific AU plugins (example, replace with actual paths) ---")
        # specific_paths_to_check = [
        #     Path("/Library/Audio/Plug-Ins/Components/AUNewPitch.component"),
        #     Path("/path/to/nonexistent.component") # Example non-existent
        # ]
        # filtered_au_plugins = scanner.find_plugin_files(plugin_paths=specific_paths_to_check)
        # for p_path in filtered_au_plugins:
        #     print(p_path)
    else:
        print("AU scanning example is for macOS only.")
