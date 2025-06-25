"""
Type definitions and aliases for the pedalboard_pluginary package.
"""

from typing import Union, Dict, Any, TypedDict, Optional
import sys

if sys.version_info >= (3, 11):
    from typing import NotRequired
else:
    from typing_extensions import NotRequired

# Basic type aliases
ParameterValue = Union[float, bool, str]
PluginID = str
PluginType = str  # "vst3" or "aufx"
PluginPath = str  # String representation of path for JSON serialization


class SerializedParameter(TypedDict):
    """TypedDict for serialized plugin parameter."""
    name: str
    value: ParameterValue


class SerializedPlugin(TypedDict):
    """TypedDict for serialized plugin data."""
    id: str
    name: str
    path: str
    filename: str
    plugin_type: str
    parameters: Dict[str, SerializedParameter]
    manufacturer: NotRequired[Optional[str]]
    name_in_file: NotRequired[Optional[str]]


class CacheMetadata(TypedDict):
    """TypedDict for cache metadata."""
    version: str
    created_at: str
    updated_at: str
    plugin_count: int
    scanner_version: str


class CacheData(TypedDict):
    """TypedDict for complete cache data structure."""
    metadata: CacheMetadata
    plugins: Dict[str, SerializedPlugin]


# Type guards
def is_parameter_value(value: Any) -> bool:
    """Check if a value is a valid ParameterValue."""
    return isinstance(value, (float, bool, str))


def is_serialized_parameter(data: Any) -> bool:
    """Check if data is a valid SerializedParameter."""
    return (
        isinstance(data, dict) and
        "name" in data and
        "value" in data and
        isinstance(data["name"], str) and
        is_parameter_value(data["value"])
    )


def is_serialized_plugin(data: Any) -> bool:
    """Check if data is a valid SerializedPlugin."""
    if not isinstance(data, dict):
        return False
    
    required_fields = ["id", "name", "path", "filename", "plugin_type", "parameters"]
    for field in required_fields:
        if field not in data:
            return False
    
    # Check types of required fields
    if not all(isinstance(data[field], str) for field in ["id", "name", "path", "filename", "plugin_type"]):
        return False
    
    # Check parameters
    if not isinstance(data["parameters"], dict):
        return False
    
    for param_name, param_data in data["parameters"].items():
        if not isinstance(param_name, str) or not is_serialized_parameter(param_data):
            return False
    
    # Check optional fields
    if "manufacturer" in data and data["manufacturer"] is not None:
        if not isinstance(data["manufacturer"], str):
            return False
    
    if "name_in_file" in data and data["name_in_file"] is not None:
        if not isinstance(data["name_in_file"], str):
            return False
    
    return True