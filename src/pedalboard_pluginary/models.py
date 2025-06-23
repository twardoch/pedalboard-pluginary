# pedalboard_pluginary/models.py
"""
Dataclasses for representing plugin information.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union, Dict, Optional, Any

# ParameterValue is what we store (after conversion from pedalboard's raw param value)
ParameterValue = Union[float, bool, str]

@dataclass
class PluginParameter:
    """Represents a single parameter of a plugin."""
    name: str
    value: ParameterValue
    # Optional: Add other attributes like min_value, max_value, string_value, etc.
    # if Pedalboard consistently provides them and they are useful to store.
    # For now, keeping it simple with just name and current (default) value.
    # raw_pedalboard_value: Any # Could store the original pedalboard value if needed for debugging

@dataclass
class PluginInfo:
    """Represents a scanned audio plugin."""
    # Unique key for this plugin, e.g., "vst3/FabFilter Pro-Q 3" or "aufx/ChannelEQ"
    # This key might be different from `name` if a file contains multiple plugins or
    # if the user-facing name has characters not suitable for a key.
    # This will be the key in the main dictionary of plugins.
    id: str

    name: str # The display name of the plugin
    path: str # Path to the plugin file or bundle (as string for JSON serialization)
    filename: str # Filename of the plugin (e.g., "FabFilter Pro-Q 3.vst3")
    plugin_type: str # "vst3" or "aufx"

    # Parameters: dict where key is param name, value is PluginParameter object
    parameters: Dict[str, PluginParameter] = field(default_factory=dict)

    manufacturer: Optional[str] = None # Optional: Plugin manufacturer name

    # Optional: If a plugin file (e.g. VST3) can contain multiple uniquely identifiable
    # plugins, this field could store the specific name used to load this plugin
    # from the file, if different from the main `name`.
    # E.g. `pedalboard.load_plugin(path, plugin_name=name_in_file)`
    name_in_file: Optional[str] = None

    def __post_init__(self):
        # Ensure path is stored as a string for easier JSON serialization
        if isinstance(self.path, Path):
            self.path = str(self.path)

    # Consider adding methods for to_dict/from_dict if needed for complex serialization,
    # though dataclasses.asdict and direct instantiation usually suffice.

# Example usage:
# if __name__ == "__main__":
#     eq_param = PluginParameter(name="Frequency", value=1000.0)
#     gain_param = PluginParameter(name="Gain", value=0.0)
#     bypass_param = PluginParameter(name="Bypass", value=False)

#     example_plugin = PluginInfo(
#         id="vst3/AwesomeEQ",
#         name="Awesome EQ",
#         path="/path/to/AwesomeEQ.vst3",
#         filename="AwesomeEQ.vst3",
#         plugin_type="vst3",
#         parameters={
#             "Frequency": eq_param,
#             "Gain": gain_param,
#             "Bypass": bypass_param
#         },
#         manufacturer="MyPluginCompany"
#     )
#     import json
#     from dataclasses import asdict
#     print(json.dumps(asdict(example_plugin), indent=2))
