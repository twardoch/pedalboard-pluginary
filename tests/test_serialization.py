# tests/test_serialization.py
import pytest
from pedalboard_pluginary.serialization import PluginSerializer
from pedalboard_pluginary.models import PluginInfo, PluginParameter


class TestPluginSerializer:
    """Test suite for PluginSerializer."""
    
    def test_serialize_plugin_parameter(self):
        """Test serializing a PluginParameter."""
        param = PluginParameter(
            name="Volume",
            value=0.75,
            min_value=0.0,
            max_value=1.0,
            default_value=0.5,
            units="linear"
        )
        
        serialized = PluginSerializer.serialize_plugin_parameter(param)
        
        assert serialized["name"] == "Volume"
        assert serialized["value"] == 0.75
        assert serialized["min_value"] == 0.0
        assert serialized["max_value"] == 1.0
        assert serialized["default_value"] == 0.5
        assert serialized["units"] == "linear"
        
    def test_serialize_plugin_parameter_minimal(self):
        """Test serializing a minimal PluginParameter."""
        param = PluginParameter(name="Volume", value=0.75)
        
        serialized = PluginSerializer.serialize_plugin_parameter(param)
        
        assert serialized["name"] == "Volume"
        assert serialized["value"] == 0.75
        assert serialized["min_value"] is None
        assert serialized["max_value"] is None
        assert serialized["default_value"] is None
        assert serialized["units"] is None
        
    def test_deserialize_plugin_parameter(self):
        """Test deserializing a PluginParameter."""
        serialized = {
            "name": "Volume",
            "value": 0.75,
            "min_value": 0.0,
            "max_value": 1.0,
            "default_value": 0.5,
            "units": "linear"
        }
        
        param = PluginSerializer.deserialize_plugin_parameter(serialized)
        
        assert param.name == "Volume"
        assert param.value == 0.75
        assert param.min_value == 0.0
        assert param.max_value == 1.0
        assert param.default_value == 0.5
        assert param.units == "linear"
        
    def test_deserialize_plugin_parameter_minimal(self):
        """Test deserializing a minimal PluginParameter."""
        serialized = {
            "name": "Volume",
            "value": 0.75
        }
        
        param = PluginSerializer.deserialize_plugin_parameter(serialized)
        
        assert param.name == "Volume"
        assert param.value == 0.75
        assert param.min_value is None
        assert param.max_value is None
        assert param.default_value is None
        assert param.units is None
        
    def test_serialize_plugin_info(self):
        """Test serializing a PluginInfo."""
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
        
        serialized = PluginSerializer.serialize_plugin_info(plugin)
        
        assert serialized["id"] == "vst3/TestPlugin"
        assert serialized["name"] == "TestPlugin"
        assert serialized["path"] == "/test/path/TestPlugin.vst3"
        assert serialized["filename"] == "TestPlugin.vst3"
        assert serialized["plugin_type"] == "vst3"
        assert serialized["manufacturer"] == "TestManufacturer"
        assert serialized["name_in_file"] == "TestPlugin"
        
        assert len(serialized["parameters"]) == 2
        assert "Volume" in serialized["parameters"]
        assert "Pan" in serialized["parameters"]
        assert serialized["parameters"]["Volume"]["value"] == 0.75
        assert serialized["parameters"]["Pan"]["value"] == 0.0
        
    def test_deserialize_plugin_info(self):
        """Test deserializing a PluginInfo."""
        serialized = {
            "id": "vst3/TestPlugin",
            "name": "TestPlugin",
            "path": "/test/path/TestPlugin.vst3",
            "filename": "TestPlugin.vst3",
            "plugin_type": "vst3",
            "manufacturer": "TestManufacturer",
            "name_in_file": "TestPlugin",
            "parameters": {
                "Volume": {"name": "Volume", "value": 0.75},
                "Pan": {"name": "Pan", "value": 0.0}
            }
        }
        
        plugin = PluginSerializer.deserialize_plugin_info(serialized)
        
        assert plugin.id == "vst3/TestPlugin"
        assert plugin.name == "TestPlugin"
        assert plugin.path == "/test/path/TestPlugin.vst3"
        assert plugin.filename == "TestPlugin.vst3"
        assert plugin.plugin_type == "vst3"
        assert plugin.manufacturer == "TestManufacturer"
        assert plugin.name_in_file == "TestPlugin"
        
        assert len(plugin.parameters) == 2
        assert "Volume" in plugin.parameters
        assert "Pan" in plugin.parameters
        assert plugin.parameters["Volume"].value == 0.75
        assert plugin.parameters["Pan"].value == 0.0
        
    def test_serialize_plugins_dict(self):
        """Test serializing a dictionary of plugins."""
        plugin1 = PluginInfo(
            id="vst3/Plugin1",
            name="Plugin1",
            path="/test/path1",
            filename="Plugin1.vst3",
            plugin_type="vst3",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="Plugin1"
        )
        
        plugin2 = PluginInfo(
            id="aufx/Plugin2",
            name="Plugin2",
            path="/test/path2",
            filename="Plugin2.component",
            plugin_type="aufx",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="Plugin2"
        )
        
        plugins = {
            "vst3/Plugin1": plugin1,
            "aufx/Plugin2": plugin2
        }
        
        serialized = PluginSerializer.serialize_plugins(plugins)
        
        assert len(serialized) == 2
        assert "vst3/Plugin1" in serialized
        assert "aufx/Plugin2" in serialized
        assert serialized["vst3/Plugin1"]["name"] == "Plugin1"
        assert serialized["aufx/Plugin2"]["name"] == "Plugin2"
        
    def test_deserialize_plugins_dict(self):
        """Test deserializing a dictionary of plugins."""
        serialized = {
            "vst3/Plugin1": {
                "id": "vst3/Plugin1",
                "name": "Plugin1",
                "path": "/test/path1",
                "filename": "Plugin1.vst3",
                "plugin_type": "vst3",
                "parameters": {},
                "manufacturer": "TestManufacturer",
                "name_in_file": "Plugin1"
            },
            "aufx/Plugin2": {
                "id": "aufx/Plugin2",
                "name": "Plugin2",
                "path": "/test/path2",
                "filename": "Plugin2.component",
                "plugin_type": "aufx",
                "parameters": {},
                "manufacturer": "TestManufacturer",
                "name_in_file": "Plugin2"
            }
        }
        
        plugins = PluginSerializer.deserialize_plugins(serialized)
        
        assert len(plugins) == 2
        assert "vst3/Plugin1" in plugins
        assert "aufx/Plugin2" in plugins
        assert plugins["vst3/Plugin1"].name == "Plugin1"
        assert plugins["aufx/Plugin2"].name == "Plugin2"
        
    def test_round_trip_serialization(self):
        """Test round-trip serialization/deserialization."""
        volume_param = PluginParameter(
            name="Volume",
            value=0.75,
            min_value=0.0,
            max_value=1.0,
            default_value=0.5,
            units="linear"
        )
        
        original_plugin = PluginInfo(
            id="vst3/TestPlugin",
            name="TestPlugin",
            path="/test/path/TestPlugin.vst3",
            filename="TestPlugin.vst3",
            plugin_type="vst3",
            parameters={"Volume": volume_param},
            manufacturer="TestManufacturer",
            name_in_file="TestPlugin"
        )
        
        # Serialize and deserialize
        serialized = PluginSerializer.serialize_plugin_info(original_plugin)
        deserialized_plugin = PluginSerializer.deserialize_plugin_info(serialized)
        
        # Verify the plugin is identical
        assert deserialized_plugin.id == original_plugin.id
        assert deserialized_plugin.name == original_plugin.name
        assert deserialized_plugin.path == original_plugin.path
        assert deserialized_plugin.filename == original_plugin.filename
        assert deserialized_plugin.plugin_type == original_plugin.plugin_type
        assert deserialized_plugin.manufacturer == original_plugin.manufacturer
        assert deserialized_plugin.name_in_file == original_plugin.name_in_file
        
        # Verify parameters are identical
        assert len(deserialized_plugin.parameters) == len(original_plugin.parameters)
        for param_name, param in original_plugin.parameters.items():
            assert param_name in deserialized_plugin.parameters
            deserialized_param = deserialized_plugin.parameters[param_name]
            assert deserialized_param.name == param.name
            assert deserialized_param.value == param.value
            assert deserialized_param.min_value == param.min_value
            assert deserialized_param.max_value == param.max_value
            assert deserialized_param.default_value == param.default_value
            assert deserialized_param.units == param.units