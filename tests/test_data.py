import os
from pathlib import Path
from unittest.mock import patch

from pedalboard_pluginary.data import APP_NAME, get_cache_path


@patch("platform.system", return_value="Windows")
def test_get_cache_path_windows(mock_platform_system):
    appdata = "C:\\Users\\TestUser\\AppData"
    with patch.dict(os.environ, {"APPDATA": appdata}):
        path = get_cache_path("test_cache")
        # Build the expected path with Path so separators match the host OS.
        assert str(path) == str(Path(appdata) / APP_NAME / "test_cache")


@patch("platform.system", return_value="Darwin")
def test_get_cache_path_macos(mock_platform_system):
    # Test for macOS when APPDATA is not set (should not be used)
    # and XDG_CACHE_HOME is not set (should not be used)
    with patch.dict(os.environ, {}, clear=True):
        path = get_cache_path("test_cache")
        home = os.path.expanduser("~")
        expected_path = (
            f"{home}/Library/Application Support/"
            "com.twardoch.pedalboard-pluginary/test_cache"
        )
        assert str(path) == expected_path


@patch("platform.system", return_value="Linux")
def test_get_cache_path_linux_xdg_set(mock_platform_system):
    xdg_cache_dir = "/custom/xdg/cache"
    with patch.dict(os.environ, {"XDG_CACHE_HOME": xdg_cache_dir}, clear=True):
        path = get_cache_path("test_cache")
        expected_path = f"{xdg_cache_dir}/com.twardoch.pedalboard-pluginary/test_cache"
        assert str(path) == expected_path


@patch("platform.system", return_value="Linux")
def test_get_cache_path_linux_xdg_not_set(mock_platform_system):
    # Test when XDG_CACHE_HOME is not set
    with patch.dict(os.environ, {}, clear=True):  # Ensure XDG_CACHE_HOME is not set
        path = get_cache_path("test_cache")
        home = os.path.expanduser("~")
        expected_path = f"{home}/.cache/com.twardoch.pedalboard-pluginary/test_cache"
        assert str(path) == expected_path
