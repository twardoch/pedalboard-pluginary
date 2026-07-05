"""Type stubs for pedalboard library."""

from pathlib import Path
from typing import Any

# Parameter value types that pedalboard can return
ParameterValue = float | int | bool | str

class Plugin:
    """Base plugin class."""

    # Core attributes that all plugins have
    parameters: dict[str, ParameterValue]
    name: str
    manufacturer: str | None

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class AudioUnitPlugin(Plugin):
    """Audio Unit plugin class."""

    pass

class VST3Plugin(Plugin):
    """VST3 plugin class."""

    pass

# Plugin loading function
def load_plugin(
    path_or_name: str | Path,
    plugin_name: str | None = None,
    disable_caching: bool = False,
    **kwargs: Any,
) -> Plugin: ...

# Re-export common types
__all__ = [
    "Plugin",
    "AudioUnitPlugin",
    "VST3Plugin",
    "load_plugin",
    "ParameterValue",
]
