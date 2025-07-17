# tests/test_core.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

from pedalboard_pluginary.core import PedalboardPluginary
from pedalboard_pluginary.models import PluginInfo, PluginParameter
from pedalboard_pluginary.exceptions import PluginaryError


class TestPedalboardPluginary:
    """Test suite for PedalboardPluginary core class."""
    
    def test_init_default(self):
        """Test PedalboardPluginary initialization with default parameters."""
        pluginary = PedalboardPluginary()
        assert pluginary.plugins == {}
        assert pluginary.scanner is not None
        
    def test_init_custom_scanner(self):
        """Test PedalboardPluginary initialization with custom scanner."""
        mock_scanner = Mock()
        pluginary = PedalboardPluginary(scanner=mock_scanner)
        assert pluginary.scanner == mock_scanner
        
    @patch('pedalboard_pluginary.core.PedalboardPluginary.load_data')
    def test_load_data_called_on_init(self, mock_load_data):
        """Test that load_data is called during initialization."""
        PedalboardPluginary()
        mock_load_data.assert_called_once()
        
    @patch('pedalboard_pluginary.data.load_json_file')
    def test_load_data_success(self, mock_load_json):
        """Test successful loading of plugin data."""
        mock_plugin_data = {
            "vst3/TestPlugin": {
                "id": "vst3/TestPlugin",
                "name": "TestPlugin",
                "path": "/test/path",
                "filename": "TestPlugin.vst3",
                "plugin_type": "vst3",
                "parameters": {},
                "manufacturer": "TestManufacturer",
                "name_in_file": "TestPlugin"
            }
        }
        mock_load_json.return_value = mock_plugin_data
        
        pluginary = PedalboardPluginary()
        assert len(pluginary.plugins) == 1
        assert "vst3/TestPlugin" in pluginary.plugins
        assert pluginary.plugins["vst3/TestPlugin"].name == "TestPlugin"
        
    @patch('pedalboard_pluginary.data.load_json_file')
    def test_load_data_file_not_found(self, mock_load_json):
        """Test handling of missing cache file."""
        mock_load_json.side_effect = FileNotFoundError("Cache file not found")
        
        pluginary = PedalboardPluginary()
        assert pluginary.plugins == {}
        
    @patch('pedalboard_pluginary.data.load_json_file')
    def test_load_data_invalid_json(self, mock_load_json):
        """Test handling of invalid JSON in cache file."""
        mock_load_json.side_effect = json.JSONDecodeError("Invalid JSON", "test", 0)
        
        pluginary = PedalboardPluginary()
        assert pluginary.plugins == {}
        
    def test_full_scan_delegates_to_scanner(self):
        """Test that full_scan delegates to scanner."""
        mock_scanner = Mock()
        pluginary = PedalboardPluginary(scanner=mock_scanner)
        
        pluginary.full_scan()
        mock_scanner.rescan.assert_called_once()
        
    def test_update_scan_delegates_to_scanner(self):
        """Test that update_scan delegates to scanner."""
        mock_scanner = Mock()
        pluginary = PedalboardPluginary(scanner=mock_scanner)
        
        pluginary.update_scan()
        mock_scanner.update.assert_called_once()
        
    def test_get_plugin_existing(self):
        """Test getting an existing plugin."""
        plugin_info = PluginInfo(
            id="vst3/TestPlugin",
            name="TestPlugin",
            path="/test/path",
            filename="TestPlugin.vst3",
            plugin_type="vst3",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="TestPlugin"
        )
        
        pluginary = PedalboardPluginary()
        pluginary.plugins = {"vst3/TestPlugin": plugin_info}
        
        result = pluginary.get_plugin("vst3/TestPlugin")
        assert result == plugin_info
        
    def test_get_plugin_non_existing(self):
        """Test getting a non-existing plugin."""
        pluginary = PedalboardPluginary()
        
        result = pluginary.get_plugin("non/existing")
        assert result is None
        
    def test_list_plugins_empty(self):
        """Test listing plugins when none exist."""
        pluginary = PedalboardPluginary()
        
        result = pluginary.list_plugins()
        assert result == {}
        
    def test_list_plugins_with_filter(self):
        """Test listing plugins with type filter."""
        vst3_plugin = PluginInfo(
            id="vst3/TestPlugin",
            name="TestPlugin",
            path="/test/path",
            filename="TestPlugin.vst3",
            plugin_type="vst3",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="TestPlugin"
        )
        
        au_plugin = PluginInfo(
            id="aufx/TestAU",
            name="TestAU",
            path="/test/path",
            filename="TestAU.component",
            plugin_type="aufx",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="TestAU"
        )
        
        pluginary = PedalboardPluginary()
        pluginary.plugins = {
            "vst3/TestPlugin": vst3_plugin,
            "aufx/TestAU": au_plugin
        }
        
        result = pluginary.list_plugins(plugin_type="vst3")
        assert len(result) == 1
        assert "vst3/TestPlugin" in result
        
    def test_list_plugins_with_manufacturer_filter(self):
        """Test listing plugins with manufacturer filter."""
        plugin1 = PluginInfo(
            id="vst3/Plugin1",
            name="Plugin1",
            path="/test/path1",
            filename="Plugin1.vst3",
            plugin_type="vst3",
            parameters={},
            manufacturer="FabFilter",
            name_in_file="Plugin1"
        )
        
        plugin2 = PluginInfo(
            id="vst3/Plugin2",
            name="Plugin2",
            path="/test/path2",
            filename="Plugin2.vst3",
            plugin_type="vst3",
            parameters={},
            manufacturer="Waves",
            name_in_file="Plugin2"
        )
        
        pluginary = PedalboardPluginary()
        pluginary.plugins = {
            "vst3/Plugin1": plugin1,
            "vst3/Plugin2": plugin2
        }
        
        result = pluginary.list_plugins(manufacturer="FabFilter")
        assert len(result) == 1
        assert "vst3/Plugin1" in result
        
    def test_plugin_count(self):
        """Test getting plugin count."""
        pluginary = PedalboardPluginary()
        assert pluginary.plugin_count == 0
        
        pluginary.plugins = {"test": Mock()}
        assert pluginary.plugin_count == 1