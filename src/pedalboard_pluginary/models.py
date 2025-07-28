# pedalboard_pluginary/models.py
"""
Dataclasses for representing plugin information.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .types import ParameterValue

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

