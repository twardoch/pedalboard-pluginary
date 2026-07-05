# tests/test_serialization.py
from pedalboard_pluginary.models import PluginInfo, PluginParameter
from pedalboard_pluginary.serialization import PluginSerializer


class TestPluginSerializer:
    """Test suite for PluginSerializer."""

    def test_parameter_to_dict(self):
        """Test serializing a PluginParameter to a name/value dict."""
        param = PluginParameter(name="Volume", value=0.75)

        serialized = PluginSerializer.parameter_to_dict(param)

        assert serialized == {"name": "Volume", "value": 0.75}

    def test_dict_to_parameter(self):
        """Test deserializing a PluginParameter from a name/value dict."""
        param = PluginSerializer.dict_to_parameter({"name": "Volume", "value": 0.75})

        assert param is not None
        assert param.name == "Volume"
        assert param.value == 0.75

    def test_dict_to_parameter_invalid(self):
        """Test that invalid parameter data returns None."""
        assert PluginSerializer.dict_to_parameter({"name": "Volume"}) is None

    def test_plugin_to_dict(self):
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
            name_in_file="TestPlugin",
        )

        serialized = PluginSerializer.plugin_to_dict(plugin)

        assert serialized["id"] == "vst3/TestPlugin"
        assert serialized["name"] == "TestPlugin"
        assert serialized["path"] == "/test/path/TestPlugin.vst3"
        assert serialized["filename"] == "TestPlugin.vst3"
        assert serialized["plugin_type"] == "vst3"
        assert serialized["manufacturer"] == "TestManufacturer"
        assert serialized["name_in_file"] == "TestPlugin"

        assert len(serialized["parameters"]) == 2
        assert serialized["parameters"]["Volume"] == {"name": "Volume", "value": 0.75}
        assert serialized["parameters"]["Pan"] == {"name": "Pan", "value": 0.0}

    def test_dict_to_plugin(self):
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
                "Pan": {"name": "Pan", "value": 0.0},
            },
        }

        plugin = PluginSerializer.dict_to_plugin(serialized)

        assert plugin is not None
        assert plugin.id == "vst3/TestPlugin"
        assert plugin.name == "TestPlugin"
        assert plugin.path == "/test/path/TestPlugin.vst3"
        assert plugin.filename == "TestPlugin.vst3"
        assert plugin.plugin_type == "vst3"
        assert plugin.manufacturer == "TestManufacturer"
        assert plugin.name_in_file == "TestPlugin"

        assert len(plugin.parameters) == 2
        assert plugin.parameters["Volume"].value == 0.75
        assert plugin.parameters["Pan"].value == 0.0

    def test_dict_to_plugin_invalid(self):
        """Test that invalid plugin data returns None."""
        assert PluginSerializer.dict_to_plugin({"id": "vst3/Broken"}) is None

    def test_serialize_plugins_dict(self):
        """Test serializing a dictionary of plugins via plugin_to_dict."""
        plugin1 = PluginInfo(
            id="vst3/Plugin1",
            name="Plugin1",
            path="/test/path1",
            filename="Plugin1.vst3",
            plugin_type="vst3",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="Plugin1",
        )

        plugin2 = PluginInfo(
            id="aufx/Plugin2",
            name="Plugin2",
            path="/test/path2",
            filename="Plugin2.component",
            plugin_type="aufx",
            parameters={},
            manufacturer="TestManufacturer",
            name_in_file="Plugin2",
        )

        plugins = {"vst3/Plugin1": plugin1, "aufx/Plugin2": plugin2}
        serialized = {
            pid: PluginSerializer.plugin_to_dict(p) for pid, p in plugins.items()
        }

        assert len(serialized) == 2
        assert serialized["vst3/Plugin1"]["name"] == "Plugin1"
        assert serialized["aufx/Plugin2"]["name"] == "Plugin2"

    def test_deserialize_plugins_dict(self):
        """Test deserializing a dictionary of plugins via dict_to_plugin."""
        serialized = {
            "vst3/Plugin1": {
                "id": "vst3/Plugin1",
                "name": "Plugin1",
                "path": "/test/path1",
                "filename": "Plugin1.vst3",
                "plugin_type": "vst3",
                "parameters": {},
                "manufacturer": "TestManufacturer",
                "name_in_file": "Plugin1",
            },
            "aufx/Plugin2": {
                "id": "aufx/Plugin2",
                "name": "Plugin2",
                "path": "/test/path2",
                "filename": "Plugin2.component",
                "plugin_type": "aufx",
                "parameters": {},
                "manufacturer": "TestManufacturer",
                "name_in_file": "Plugin2",
            },
        }

        plugins = {
            pid: PluginSerializer.dict_to_plugin(data)
            for pid, data in serialized.items()
        }

        assert len(plugins) == 2
        assert plugins["vst3/Plugin1"].name == "Plugin1"
        assert plugins["aufx/Plugin2"].name == "Plugin2"

    def test_round_trip_serialization(self):
        """Test round-trip serialization/deserialization."""
        volume_param = PluginParameter(name="Volume", value=0.75)

        original_plugin = PluginInfo(
            id="vst3/TestPlugin",
            name="TestPlugin",
            path="/test/path/TestPlugin.vst3",
            filename="TestPlugin.vst3",
            plugin_type="vst3",
            parameters={"Volume": volume_param},
            manufacturer="TestManufacturer",
            name_in_file="TestPlugin",
        )

        serialized = PluginSerializer.plugin_to_dict(original_plugin)
        deserialized_plugin = PluginSerializer.dict_to_plugin(serialized)

        assert deserialized_plugin is not None
        assert deserialized_plugin.id == original_plugin.id
        assert deserialized_plugin.name == original_plugin.name
        assert deserialized_plugin.path == original_plugin.path
        assert deserialized_plugin.filename == original_plugin.filename
        assert deserialized_plugin.plugin_type == original_plugin.plugin_type
        assert deserialized_plugin.manufacturer == original_plugin.manufacturer
        assert deserialized_plugin.name_in_file == original_plugin.name_in_file

        assert len(deserialized_plugin.parameters) == len(original_plugin.parameters)
        for param_name, param in original_plugin.parameters.items():
            deserialized_param = deserialized_plugin.parameters[param_name]
            assert deserialized_param.name == param.name
            assert deserialized_param.value == param.value
