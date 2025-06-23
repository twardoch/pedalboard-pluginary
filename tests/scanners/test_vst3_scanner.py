# tests/scanners/test_vst3_scanner.py
import os
import platform
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from pedalboard_pluginary.scanners.vst3_scanner import VST3Scanner

# Helper to create dummy VST3 files and folders
def create_dummy_vst3_structure(tmp_path, structure):
    """
    Creates a dummy VST3 plugin directory structure.
    structure is a dict like:
    {
        "folder_name": ["plugin1.vst3", "plugin2.vst3", {"subfolder": ["plugin3.vst3"]}]
    }
    """
    for name, contents in structure.items():
        current_path = tmp_path / name
        current_path.mkdir(parents=True, exist_ok=True)
        for item in contents:
            if isinstance(item, str): # It's a file
                (current_path / item).touch()
            elif isinstance(item, dict): # It's a sub-structure
                create_dummy_vst3_structure(current_path, item)


@pytest.fixture
def vst3_scanner_instance():
    return VST3Scanner(ignores=set())

@pytest.fixture
def vst3_scanner_with_ignores_instance():
    return VST3Scanner(ignores={"vst3/IgnoredPlugin"})


class TestVST3Scanner:

    @patch('platform.system', return_value='Windows')
    @patch.dict(os.environ, {"ProgramFiles": "C:\\Program Files", "ProgramFiles(x86)": "C:\\Program Files (x86)"})
    def test_get_default_vst3_folders_windows(self, mock_platform_system, vst3_scanner_instance, tmp_path):
        # Create dummy common VST3 folders for Windows
        win_vst3_path1 = tmp_path / "Program Files" / "Common Files" / "VST3"
        win_vst3_path1.mkdir(parents=True, exist_ok=True)
        win_vst3_path2 = tmp_path / "Program Files (x86)" / "Common Files" / "VST3"
        win_vst3_path2.mkdir(parents=True, exist_ok=True)

        # Patch os.getenv to return mocked ProgramFiles paths relative to tmp_path
        def mock_getenv_windows(var_name, default=None):
            if var_name == "ProgramFiles":
                return str(tmp_path / "Program Files")
            if var_name == "ProgramFiles(x86)":
                return str(tmp_path / "Program Files (x86)")
            return default

        with patch('os.getenv', side_effect=mock_getenv_windows):
            folders = vst3_scanner_instance._get_default_vst3_folders()
            assert Path(win_vst3_path1).resolve() in folders
            assert Path(win_vst3_path2).resolve() in folders

    @patch('platform.system', return_value='Darwin')
    def test_get_default_vst3_folders_macos(self, mock_platform_system, vst3_scanner_instance, tmp_path):
        mac_vst3_path1 = tmp_path / "Library" / "Audio" / "Plug-Ins" / "VST3" # System
        mac_vst3_path1.mkdir(parents=True, exist_ok=True)
        # User path needs to be mocked for expanduser
        user_home_vst3_path = tmp_path / "Users" / "testuser" / "Library" / "Audio" / "Plug-Ins" / "VST3"
        user_home_vst3_path.mkdir(parents=True, exist_ok=True)

        with patch('pathlib.Path.home', return_value=tmp_path / "Users" / "testuser"), \
             patch('pathlib.Path.expanduser', side_effect=lambda p: p if not str(p).startswith("~") else user_home_vst3_path):
            # Mock /Library path to point to our tmp_path version
            original_path_init = Path.__init__
            def mocked_path_init(self, *args, **kwargs):
                if args and args[0] == "/Library/Audio/Plug-Ins/VST3":
                    args = (str(mac_vst3_path1),) + args[1:]
                original_path_init(self, *args, **kwargs)

            with patch('pathlib.Path.__init__', mocked_path_init):
                 folders = vst3_scanner_instance._get_default_vst3_folders()
                 assert user_home_vst3_path.resolve() in folders
                 assert mac_vst3_path1.resolve() in folders


    @patch('platform.system', return_value='Linux')
    def test_get_default_vst3_folders_linux(self, mock_platform_system, vst3_scanner_instance, tmp_path):
        linux_vst3_path1 = tmp_path / ".vst3" # User
        linux_vst3_path1.mkdir(parents=True, exist_ok=True)
        linux_vst3_path2 = tmp_path / "usr" / "lib" / "vst3" # System
        linux_vst3_path2.mkdir(parents=True, exist_ok=True)

        with patch('pathlib.Path.home', return_value=tmp_path), \
             patch('pathlib.Path.expanduser', side_effect=lambda p: p if not str(p).startswith("~") else linux_vst3_path1):
            # Mock /usr/lib/vst3 to point to our tmp_path version
            original_path_init = Path.__init__
            def mocked_path_init(self, *args, **kwargs):
                if args and args[0] == "/usr/lib/vst3":
                    args = (str(linux_vst3_path2),) + args[1:]
                elif args and args[0] == "/usr/local/lib/vst3": # Also mock this common path
                     args = (str(tmp_path / "usr" / "local" / "lib" / "vst3"),) + args[1:]
                     (tmp_path / "usr" / "local" / "lib" / "vst3").mkdir(parents=True, exist_ok=True)

                original_path_init(self, *args, **kwargs)

            with patch('pathlib.Path.__init__', mocked_path_init):
                folders = vst3_scanner_instance._get_default_vst3_folders()
                assert linux_vst3_path1.resolve() in folders
                assert linux_vst3_path2.resolve() in folders


    def test_find_plugin_files_discovery(self, vst3_scanner_instance, tmp_path):
        # Create a dummy default folder and put some plugins in it
        default_folder = tmp_path / "DefaultVST3s"
        default_folder.mkdir()
        (default_folder / "PluginA.vst3").touch()
        (default_folder / "PluginB.vst3").touch()

        with patch.object(VST3Scanner, '_get_default_vst3_folders', return_value=[default_folder]):
            found_plugins = vst3_scanner_instance.find_plugin_files()
            assert len(found_plugins) == 2
            assert default_folder / "PluginA.vst3" in found_plugins
            assert default_folder / "PluginB.vst3" in found_plugins

    def test_find_plugin_files_with_extra_folders(self, vst3_scanner_instance, tmp_path):
        extra_folder1 = tmp_path / "ExtraVST3s1"
        extra_folder1.mkdir()
        (extra_folder1 / "PluginC.vst3").touch()

        extra_folder2 = tmp_path / "ExtraVST3s2" # Non-existent

        # Mock default folders to be empty to isolate test to extra_folders
        with patch.object(VST3Scanner, '_get_default_vst3_folders', return_value=[]):
            found_plugins = vst3_scanner_instance.find_plugin_files(extra_folders=[str(extra_folder1), str(extra_folder2)])
            assert len(found_plugins) == 1
            assert extra_folder1 / "PluginC.vst3" in found_plugins

    def test_find_plugin_files_with_specific_paths(self, vst3_scanner_instance, tmp_path):
        plugin_path1 = tmp_path / "SpecificPlugin1.vst3"
        plugin_path1.touch()
        plugin_path2 = tmp_path / "SpecificPlugin2.vst3" # Non-existent for this call

        found_plugins = vst3_scanner_instance.find_plugin_files(plugin_paths=[plugin_path1, plugin_path2])
        assert len(found_plugins) == 1
        assert plugin_path1 in found_plugins # plugin_path2 should not be found as it doesn't exist yet

    def test_find_plugin_files_with_ignores(self, vst3_scanner_with_ignores_instance, tmp_path):
        default_folder = tmp_path / "VST3WithIgnores"
        default_folder.mkdir()
        (default_folder / "NormalPlugin.vst3").touch()
        (default_folder / "IgnoredPlugin.vst3").touch() # This one has stem "IgnoredPlugin"

        with patch.object(VST3Scanner, '_get_default_vst3_folders', return_value=[default_folder]):
            found_plugins = vst3_scanner_with_ignores_instance.find_plugin_files()
            assert len(found_plugins) == 1
            assert default_folder / "NormalPlugin.vst3" in found_plugins
            assert default_folder / "IgnoredPlugin.vst3" not in found_plugins

    def test_find_plugin_files_no_folders_exist(self, vst3_scanner_instance):
        with patch.object(VST3Scanner, '_get_default_vst3_folders', return_value=[]):
            found_plugins = vst3_scanner_instance.find_plugin_files()
            assert len(found_plugins) == 0

    def test_find_plugin_files_skips_directories_with_vst3_suffix(self, vst3_scanner_instance, tmp_path):
        default_folder = tmp_path / "VST3WithDirs"
        default_folder.mkdir()
        (default_folder / "RealPlugin.vst3").touch()
        (default_folder / "FakePlugin.vst3").mkdir() # A directory named like a plugin

        with patch.object(VST3Scanner, '_get_default_vst3_folders', return_value=[default_folder]):
            found_plugins = vst3_scanner_instance.find_plugin_files()
            assert len(found_plugins) == 1
            assert default_folder / "RealPlugin.vst3" in found_plugins
            assert default_folder / "FakePlugin.vst3" not in found_plugins

# TODO: Test case where a plugin_path provided to find_plugin_files is a directory (should be ignored)
# TODO: Test case with symlinks if relevant (Path.resolve() should handle them, but good to be aware)
# TODO: Test case for duplicate plugin paths from overlapping folder definitions (should be unique)
#       (find_plugin_files uses a set internally for discovery before sorting, so this should be handled)
