# tests/test_core.py
from unittest.mock import Mock, patch

from pedalboard_pluginary.core import PedalboardPluginary
from pedalboard_pluginary.models import PluginInfo, PluginParameter


def make_plugin(plugin_id, name, plugin_type, manufacturer=None, parameters=None):
    """Build a PluginInfo for use as cache.load() output."""
    return PluginInfo(
        id=plugin_id,
        name=name,
        path=f"/plugins/{name}",
        filename=f"{name}.{plugin_type}",
        plugin_type=plugin_type,
        parameters=parameters or {},
        manufacturer=manufacturer,
        name_in_file=name,
    )


class TestPedalboardPluginary:
    """Test suite for PedalboardPluginary core class."""

    @patch("pedalboard_pluginary.core.IsolatedPedalboardScanner")
    @patch("pedalboard_pluginary.core.SQLiteCacheBackend")
    def test_init_builds_cache_and_scanner(self, mock_cache_cls, mock_scanner_cls):
        """PedalboardPluginary builds its own cache and scanner on init."""
        pluginary = PedalboardPluginary()

        assert pluginary.cache is mock_cache_cls.return_value
        assert pluginary.scanner is mock_scanner_cls.return_value

    @patch("pedalboard_pluginary.core.IsolatedPedalboardScanner")
    @patch("pedalboard_pluginary.core.SQLiteCacheBackend")
    def test_init_forwards_scanner_kwargs(self, mock_cache_cls, mock_scanner_cls):
        """Extra kwargs are forwarded to the scanner constructor."""
        PedalboardPluginary(max_workers=2, verbose=True)

        mock_scanner_cls.assert_called_once_with(max_workers=2, verbose=True)

    @patch("pedalboard_pluginary.core.IsolatedPedalboardScanner")
    @patch("pedalboard_pluginary.core.SQLiteCacheBackend")
    def test_scan_delegates_to_scanner(self, mock_cache_cls, mock_scanner_cls):
        """scan() delegates to the scanner with rescan/extra_folders."""
        pluginary = PedalboardPluginary()

        pluginary.scan(rescan=True, extra_folders=["/extra"])

        pluginary.scanner.scan.assert_called_once_with(
            rescan=True, extra_folders=["/extra"]
        )

    @patch("pedalboard_pluginary.core.IsolatedPedalboardScanner")
    @patch("pedalboard_pluginary.core.SQLiteCacheBackend")
    def test_list_plugins_empty(self, mock_cache_cls, mock_scanner_cls):
        """list_plugins returns an empty list when the cache is empty."""
        pluginary = PedalboardPluginary()
        pluginary.cache = Mock()
        pluginary.cache.load.return_value = {}

        assert pluginary.list_plugins() == []

    @patch("pedalboard_pluginary.core.IsolatedPedalboardScanner")
    @patch("pedalboard_pluginary.core.SQLiteCacheBackend")
    def test_list_plugins_returns_dicts(self, mock_cache_cls, mock_scanner_cls):
        """list_plugins returns a list of dicts with the expected keys."""
        pluginary = PedalboardPluginary()
        pluginary.cache = Mock()
        pluginary.cache.load.return_value = {
            "vst3/TestPlugin": make_plugin(
                "vst3/TestPlugin",
                "TestPlugin",
                "vst3",
                manufacturer="FabFilter",
                parameters={"Gain": PluginParameter(name="Gain", value=0.5)},
            )
        }

        result = pluginary.list_plugins()

        assert isinstance(result, list)
        assert len(result) == 1
        entry = result[0]
        assert entry["id"] == "vst3/TestPlugin"
        assert entry["name"] == "TestPlugin"
        assert entry["type"] == "vst3"
        assert entry["manufacturer"] == "FabFilter"
        assert entry["params"] == {"Gain": 0.5}

    @patch("pedalboard_pluginary.core.IsolatedPedalboardScanner")
    @patch("pedalboard_pluginary.core.SQLiteCacheBackend")
    def test_list_plugins_name_filter(self, mock_cache_cls, mock_scanner_cls):
        """The name filter matches on a case-insensitive substring."""
        pluginary = PedalboardPluginary()
        pluginary.cache = Mock()
        pluginary.cache.load.return_value = {
            "vst3/ProQ": make_plugin("vst3/ProQ", "Pro-Q 3", "vst3"),
            "vst3/Reverb": make_plugin("vst3/Reverb", "Big Reverb", "vst3"),
        }

        result = pluginary.list_plugins(name="pro-q")

        assert [p["id"] for p in result] == ["vst3/ProQ"]

    @patch("pedalboard_pluginary.core.IsolatedPedalboardScanner")
    @patch("pedalboard_pluginary.core.SQLiteCacheBackend")
    def test_list_plugins_manufacturer_filter(self, mock_cache_cls, mock_scanner_cls):
        """The manufacturer filter matches on a case-insensitive substring."""
        pluginary = PedalboardPluginary()
        pluginary.cache = Mock()
        pluginary.cache.load.return_value = {
            "vst3/Plugin1": make_plugin("vst3/Plugin1", "Plugin1", "vst3", "FabFilter"),
            "vst3/Plugin2": make_plugin("vst3/Plugin2", "Plugin2", "vst3", "Waves"),
        }

        result = pluginary.list_plugins(manufacturer="fabfilter")

        assert [p["id"] for p in result] == ["vst3/Plugin1"]

    @patch("pedalboard_pluginary.core.IsolatedPedalboardScanner")
    @patch("pedalboard_pluginary.core.SQLiteCacheBackend")
    def test_list_plugins_type_filter(self, mock_cache_cls, mock_scanner_cls):
        """The type filter matches on an exact plugin_type."""
        pluginary = PedalboardPluginary()
        pluginary.cache = Mock()
        pluginary.cache.load.return_value = {
            "vst3/Plugin1": make_plugin("vst3/Plugin1", "Plugin1", "vst3"),
            "aufx/Plugin2": make_plugin("aufx/Plugin2", "Plugin2", "aufx"),
        }

        result = pluginary.list_plugins(type="vst3")

        assert [p["id"] for p in result] == ["vst3/Plugin1"]

    @patch("pedalboard_pluginary.core.IsolatedPedalboardScanner")
    @patch("pedalboard_pluginary.core.SQLiteCacheBackend")
    def test_get_plugin_details_existing(self, mock_cache_cls, mock_scanner_cls):
        """get_plugin_details returns a dict for a known plugin id."""
        pluginary = PedalboardPluginary()
        pluginary.cache = Mock()
        pluginary.cache.load.return_value = {
            "vst3/TestPlugin": make_plugin(
                "vst3/TestPlugin", "TestPlugin", "vst3", "FabFilter"
            )
        }

        result = pluginary.get_plugin_details("vst3/TestPlugin")

        assert result is not None
        assert result["id"] == "vst3/TestPlugin"
        assert result["name"] == "TestPlugin"
        assert result["manufacturer"] == "FabFilter"

    @patch("pedalboard_pluginary.core.IsolatedPedalboardScanner")
    @patch("pedalboard_pluginary.core.SQLiteCacheBackend")
    def test_get_plugin_details_missing(self, mock_cache_cls, mock_scanner_cls):
        """get_plugin_details returns None for an unknown plugin id."""
        pluginary = PedalboardPluginary()
        pluginary.cache = Mock()
        pluginary.cache.load.return_value = {}

        assert pluginary.get_plugin_details("non/existing") is None
