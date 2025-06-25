"""Type stubs for pedalboard library."""

from typing import Dict, Union, Any, Optional, TypeVar
from pathlib import Path

# Parameter value types that pedalboard can return
ParameterValue = Union[float, int, bool, str]

class Plugin:
    """Base plugin class."""
    
    # Core attributes that all plugins have
    parameters: Dict[str, ParameterValue]
    name: str
    manufacturer: Optional[str]
    
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class AudioUnitPlugin(Plugin):
    """Audio Unit plugin class."""
    pass

class VST3Plugin(Plugin):
    """VST3 plugin class."""
    pass

# Plugin loading function
def load_plugin(
    path_or_name: Union[str, Path], 
    plugin_name: Optional[str] = None,
    disable_caching: bool = False,
    **kwargs: Any
) -> Plugin: ...

# Re-export common types
__all__ = [
    "Plugin",
    "AudioUnitPlugin", 
    "VST3Plugin",
    "load_plugin",
    "ParameterValue",
]