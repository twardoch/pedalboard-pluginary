import os
from pedalboard_pluginary.data import get_cache_path
from unittest.mock import patch

def test_get_cache_path_windows():
    with patch.dict(os.environ, {"APPDATA": "C:\\Users\\TestUser\\AppData"}):
        path = get_cache_path("test_cache")
        assert str(path) == "C:\\Users\\TestUser\\AppData\\com.twardoch.pedalboard-pluginary\\test_cache.json"

def test_get_cache_path_non_windows():
    with patch.dict(os.environ, {}, clear=True):
        path = get_cache_path("test_cache")
        home = os.path.expanduser("~")
        expected_path = f"{home}/Library/Application Support/com.twardoch.pedalboard-pluginary/test_cache.json"
        assert str(path) == expected_path
