"""
Constants and configuration values for pedalboard_pluginary.
"""

from typing import Final

# Application metadata
APP_NAME: Final[str] = "com.twardoch.pedalboard-pluginary"
APP_VERSION: Final[str] = "0.1.0"  # TODO: Get from package metadata

# Cache configuration
CACHE_VERSION: Final[str] = "2.0.0"
PLUGINS_CACHE_FILENAME: Final[str] = "plugins"
IGNORES_CACHE_FILENAME: Final[str] = "ignores"

# Scanner configuration
DEFAULT_SCAN_TIMEOUT: Final[int] = 10  # seconds
MAX_SCAN_RETRIES: Final[int] = 3
SCAN_RETRY_DELAY: Final[float] = 1.0  # seconds

# Plugin types
PLUGIN_TYPE_VST3: Final[str] = "vst3"
PLUGIN_TYPE_AU: Final[str] = "aufx"
SUPPORTED_PLUGIN_TYPES: Final[list[str]] = [PLUGIN_TYPE_VST3, PLUGIN_TYPE_AU]

# File extensions
VST3_EXTENSION: Final[str] = ".vst3"
AU_EXTENSION: Final[str] = ".component"

# Platform names
PLATFORM_WINDOWS: Final[str] = "Windows"
PLATFORM_MACOS: Final[str] = "Darwin"
PLATFORM_LINUX: Final[str] = "Linux"

# Progress reporting
DEFAULT_PROGRESS_BAR_WIDTH: Final[int] = 80
PROGRESS_UPDATE_INTERVAL: Final[float] = 0.1  # seconds

# Logging configuration
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# CLI configuration
DEFAULT_OUTPUT_FORMAT: Final[str] = "json"
SUPPORTED_OUTPUT_FORMATS: Final[list[str]] = ["json", "yaml", "table", "csv"]

# Resource paths
RESOURCES_PACKAGE: Final[str] = "pedalboard_pluginary.resources"
DEFAULT_IGNORES_FILENAME: Final[str] = "default_ignores.json"