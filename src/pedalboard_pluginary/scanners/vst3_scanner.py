# pedalboard_pluginary/scanners/vst3_scanner.py
"""
Handles scanning of VST3 plugins.
"""
import itertools
import logging
import os
import platform
from pathlib import Path
from typing import List, Set, Optional, Any, Dict

# Assuming models.py will be created with PluginInfo, PluginParameter
# from ..models import PluginInfo, PluginParameter
# For now, using Dict[str, Any] as placeholder
PluginDict = Dict[str, Any]
ParamDict = Dict[str, Any] # Replace Any with Union[float, bool, str] later

logger = logging.getLogger(__name__)

class VST3Scanner:
    """Scans VST3 plugins."""

    def __init__(self, ignores: Set[str]):
        self.ignores = ignores
        # self.plugins: Dict[str, PluginInfo] = {} # To be used with typed models

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
                Path("~/.vst3").expanduser(),          # User specific
                Path("/usr/lib/vst3"),                # System wide
                Path("/usr/local/lib/vst3"),          # System wide (alternative)
            ]

        return [folder.resolve() for folder in folders if folder.exists() and folder.is_dir()]

    def find_plugin_files(
        self,
        extra_folders: Optional[List[str]] = None,
        plugin_paths: Optional[List[Path]] = None
    ) -> List[Path]:
        """
        Finds paths to VST3 plugins, respecting ignores.
        If plugin_paths is provided, it searches only those specific paths.
        Otherwise, it searches default VST3 folders and any extra_folders.
        """
        vst3_plugin_files: List[Path] = []
        plugin_type: str = "vst3"

        search_paths_to_scan: List[Path] = []

        if plugin_paths:
            # User provided specific plugin paths to check
            search_paths_to_scan = [p.resolve() for p in plugin_paths if p.exists() and p.is_file() and p.suffix == f".{plugin_type}"]
            logger.info(f"Scanning user-provided VST3 paths: {search_paths_to_scan}")
        else:
            # Discover plugins in standard and extra folders
            all_folders_to_search = self._get_default_vst3_folders()
            if extra_folders:
                all_folders_to_search.extend(Path(p).resolve() for p in extra_folders if Path(p).exists() and Path(p).is_dir())

            if not all_folders_to_search:
                logger.warning("No VST3 search folders found or specified.")
                return []

            logger.info(f"Searching for VST3 plugins in: {all_folders_to_search}")

            # Using set to avoid adding same path multiple times if folders overlap or symlinked
            discovered_plugin_path_set: Set[Path] = set()
            for folder in all_folders_to_search:
                for item in folder.glob(f"*.{plugin_type}"):
                    if item.is_file(): # Ensure it's a file, not a directory ending in .vst3
                         discovered_plugin_path_set.add(item.resolve())
            search_paths_to_scan = sorted(list(discovered_plugin_path_set))

        for plugin_path in search_paths_to_scan:
            plugin_fn_stem: str = plugin_path.stem # e.g., "MyPlugin" from "MyPlugin.vst3"
            plugin_key: str = f"{plugin_type}/{plugin_fn_stem}" # Key for ignore list

            if plugin_key in self.ignores:
                logger.debug(f"Ignoring VST3 plugin {plugin_key} based on ignores list.")
                continue

            vst3_plugin_files.append(plugin_path)

        logger.info(f"Found {len(vst3_plugin_files)} VST3 plugin files to consider.")
        return vst3_plugin_files

    # Further methods for scanning these files (get_plugin_params, etc.) will be added
    # when integrating with the main PedalboardScanner and models.

if __name__ == "__main__":
    # Example Usage
    logging.basicConfig(level=logging.DEBUG)
    # Dummy ignores for testing
    test_ignores: Set[str] = {"vst3/IgnoredPlugin", "vst3/AnotherOne"}

    scanner = VST3Scanner(ignores=test_ignores)

    print("--- Finding VST3 plugins in default locations ---")
    default_vst3_plugins = scanner.find_plugin_files()
    for p_path in default_vst3_plugins:
        print(p_path)

    # Example with extra folders (create dummy folders and .vst3 files to test)
    # Create dummy folders and files for testing this part:
    # Path("temp_vst3_folder1").mkdir(exist_ok=True)
    # Path("temp_vst3_folder1/TestPlugin1.vst3").touch()
    # Path("temp_vst3_folder2").mkdir(exist_ok=True)
    # Path("temp_vst3_folder2/TestPlugin2.vst3").touch()
    # Path("temp_vst3_folder2/IgnoredPlugin.vst3").touch() # This one should be ignored

    # print("\n--- Finding VST3 plugins with extra folders ---")
    # extra_plugin_folders = ["temp_vst3_folder1", str(Path("temp_vst3_folder2").resolve())]
    # plugins_with_extra = scanner.find_plugin_files(extra_folders=extra_plugin_folders)
    # for p_path in plugins_with_extra:
    #     print(p_path)

    # print("\n--- Finding specific VST3 plugins by path ---")
    # specific_paths = [Path("temp_vst3_folder1/TestPlugin1.vst3")]
    # if Path("temp_vst3_folder2/IgnoredPlugin.vst3").exists(): # Check if dummy file exists
    #     specific_paths.append(Path("temp_vst3_folder2/IgnoredPlugin.vst3")) # Should be ignored by name
    # specific_plugins = scanner.find_plugin_files(plugin_paths=specific_paths)
    # for p_path in specific_plugins:
    #     print(p_path)

    # Cleanup dummy folders (optional)
    # import shutil
    # if Path("temp_vst3_folder1").exists(): shutil.rmtree("temp_vst3_folder1")
    # if Path("temp_vst3_folder2").exists(): shutil.rmtree("temp_vst3_folder2")
