# tests/test_models.py
import pytest
from pedalboard_pluginary.models import PluginInfo, PluginParameter


class TestPluginParameter:
    """Test suite for PluginParameter model."""
    
    def test_init_basic(self):
        """Test basic PluginParameter initialization."""
        param = PluginParameter(name="Volume", value=0.75)
        assert param.name == "Volume"
        assert param.value == 0.75
        
    def test_init_with_optional_fields(self):
        """Test PluginParameter initialization with optional fields."""
        param = PluginParameter(
            name="Frequency",
            value=440.0,
            min_value=20.0,
            max_value=20000.0,
            default_value=440.0,
            units="Hz"
        )
        assert param.name == "Frequency"
        assert param.value == 440.0
        assert param.min_value == 20.0
        assert param.max_value == 20000.0
        assert param.default_value == 440.0
        assert param.units == "Hz"
        
    def test_equality(self):
        """Test PluginParameter equality."""
        param1 = PluginParameter(name="Volume", value=0.75)
        param2 = PluginParameter(name="Volume", value=0.75)
        param3 = PluginParameter(name="Volume", value=0.5)
        
        assert param1 == param2
        assert param1 != param3
        
    def test_str_representation(self):
        """Test string representation of PluginParameter."""
        param = PluginParameter(name="Volume", value=0.75)
        str_repr = str(param)
        assert "Volume" in str_repr
        assert "0.75" in str_repr


class TestPluginInfo:
    """Test suite for PluginInfo model."""
    
    def test_init_basic(self):
        """Test basic PluginInfo initialization."""
        plugin = PluginInfo(
            id="vst3/TestPlugin",
            name="TestPlugin",
            path="/test/path/TestPlugin.vst3",
            filename="TestPlugin.vst3",
            plugin_type="vst3",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="TestPlugin"
        )
        
        assert plugin.id == "vst3/TestPlugin"
        assert plugin.name == "TestPlugin"
        assert plugin.path == "/test/path/TestPlugin.vst3"
        assert plugin.filename == "TestPlugin.vst3"
        assert plugin.plugin_type == "vst3"
        assert plugin.parameters == {}
        assert plugin.manufacturer == "TestManufacturer"
        assert plugin.name_in_file == "TestPlugin"
        
    def test_init_with_parameters(self):
        """Test PluginInfo initialization with parameters."""
        volume_param = PluginParameter(name="Volume", value=0.75)
        pan_param = PluginParameter(name="Pan", value=0.0)
        
        plugin = PluginInfo(
            id="vst3/TestPlugin",
            name="TestPlugin",
            path="/test/path/TestPlugin.vst3",
            filename="TestPlugin.vst3",
            plugin_type="vst3",
            parameters={"Volume": volume_param, "Pan": pan_param},
            manufacturer="TestManufacturer",
            name_in_file="TestPlugin"
        )
        
        assert len(plugin.parameters) == 2
        assert "Volume" in plugin.parameters
        assert "Pan" in plugin.parameters
        assert plugin.parameters["Volume"].value == 0.75
        assert plugin.parameters["Pan"].value == 0.0
        
    def test_init_minimal(self):
        """Test PluginInfo initialization with minimal required fields."""
        plugin = PluginInfo(
            id="vst3/TestPlugin",
            name="TestPlugin",
            path="/test/path/TestPlugin.vst3",
            filename="TestPlugin.vst3",
            plugin_type="vst3",
            parameters={},
            manufacturer=None,
            name_in_file="TestPlugin"
        )
        
        assert plugin.manufacturer is None
        assert plugin.id == "vst3/TestPlugin"
        
    def test_equality(self):
        """Test PluginInfo equality."""
        plugin1 = PluginInfo(
            id="vst3/TestPlugin",
            name="TestPlugin",
            path="/test/path/TestPlugin.vst3",
            filename="TestPlugin.vst3",
            plugin_type="vst3",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="TestPlugin"
        )
        
        plugin2 = PluginInfo(
            id="vst3/TestPlugin",
            name="TestPlugin",
            path="/test/path/TestPlugin.vst3",
            filename="TestPlugin.vst3",
            plugin_type="vst3",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="TestPlugin"
        )
        
        plugin3 = PluginInfo(
            id="vst3/DifferentPlugin",
            name="DifferentPlugin",
            path="/test/path/DifferentPlugin.vst3",
            filename="DifferentPlugin.vst3",
            plugin_type="vst3",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="DifferentPlugin"
        )
        
        assert plugin1 == plugin2
        assert plugin1 != plugin3
        
    def test_str_representation(self):
        """Test string representation of PluginInfo."""
        plugin = PluginInfo(
            id="vst3/TestPlugin",
            name="TestPlugin",
            path="/test/path/TestPlugin.vst3",
            filename="TestPlugin.vst3",
            plugin_type="vst3",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="TestPlugin"
        )
        
        str_repr = str(plugin)
        assert "TestPlugin" in str_repr
        assert "vst3" in str_repr
        
    def test_parameter_count(self):
        """Test getting parameter count."""
        volume_param = PluginParameter(name="Volume", value=0.75)
        pan_param = PluginParameter(name="Pan", value=0.0)
        
        plugin = PluginInfo(
            id="vst3/TestPlugin",
            name="TestPlugin",
            path="/test/path/TestPlugin.vst3",
            filename="TestPlugin.vst3",
            plugin_type="vst3",
            parameters={"Volume": volume_param, "Pan": pan_param},
            manufacturer="TestManufacturer",
            name_in_file="TestPlugin"
        )
        
        assert len(plugin.parameters) == 2
        
    def test_au_plugin_type(self):
        """Test PluginInfo with AU plugin type."""
        plugin = PluginInfo(
            id="aufx/TestAU",
            name="TestAU",
            path="/test/path/TestAU.component",
            filename="TestAU.component",
            plugin_type="aufx",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="TestAU"
        )
        
        assert plugin.plugin_type == "aufx"
        assert plugin.filename.endswith(".component")
        
    def test_vst3_plugin_type(self):
        """Test PluginInfo with VST3 plugin type."""
        plugin = PluginInfo(
            id="vst3/TestVST3",
            name="TestVST3",
            path="/test/path/TestVST3.vst3",
            filename="TestVST3.vst3",
            plugin_type="vst3",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="TestVST3"
        )
        
        assert plugin.plugin_type == "vst3"
        assert plugin.filename.endswith(".vst3")