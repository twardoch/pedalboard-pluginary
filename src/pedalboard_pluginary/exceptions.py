"""
Custom exception hierarchy for pedalboard_pluginary.
"""

from typing import Optional


class PluginaryError(Exception):
    """Base exception for all Pluginary errors."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        """Initialize the exception with a message and optional details.
        
        Args:
            message: Main error message.
            details: Optional additional details about the error.
        """
        super().__init__(message)
        self.message = message
        self.details = details
    
    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


class ScannerError(PluginaryError):
    """Base exception for scanner-related errors."""
    pass


class PluginLoadError(ScannerError):
    """Raised when a plugin fails to load."""
    
    def __init__(self, plugin_path: str, reason: Optional[str] = None):
        """Initialize the exception.
        
        Args:
            plugin_path: Path to the plugin that failed to load.
            reason: Optional reason for the failure.
        """
        message = f"Failed to load plugin: {plugin_path}"
        super().__init__(message, reason)
        self.plugin_path = plugin_path


class PluginScanError(ScannerError):
    """Raised when scanning a plugin fails."""
    
    def __init__(self, plugin_path: str, scanner_type: str, reason: Optional[str] = None):
        """Initialize the exception.
        
        Args:
            plugin_path: Path to the plugin that failed to scan.
            scanner_type: Type of scanner that failed (e.g., 'vst3', 'aufx').
            reason: Optional reason for the failure.
        """
        message = f"Failed to scan {scanner_type} plugin: {plugin_path}"
        super().__init__(message, reason)
        self.plugin_path = plugin_path
        self.scanner_type = scanner_type


class CacheError(PluginaryError):
    """Base exception for cache-related errors."""
    pass


class CacheCorruptedError(CacheError):
    """Raised when cache file is corrupted."""
    
    def __init__(self, cache_path: str, reason: Optional[str] = None):
        """Initialize the exception.
        
        Args:
            cache_path: Path to the corrupted cache file.
            reason: Optional reason or details about the corruption.
        """
        message = f"Cache file is corrupted: {cache_path}"
        super().__init__(message, reason)
        self.cache_path = cache_path


class CacheVersionError(CacheError):
    """Raised when cache version is incompatible."""
    
    def __init__(self, expected: str, actual: str, cache_path: str):
        """Initialize the exception.
        
        Args:
            expected: Expected cache version.
            actual: Actual cache version found.
            cache_path: Path to the cache file.
        """
        message = f"Cache version mismatch: expected {expected}, got {actual}"
        details = f"Cache file: {cache_path}"
        super().__init__(message, details)
        self.expected_version = expected
        self.actual_version = actual
        self.cache_path = cache_path


class CacheWriteError(CacheError):
    """Raised when writing to cache fails."""
    
    def __init__(self, cache_path: str, reason: Optional[str] = None):
        """Initialize the exception.
        
        Args:
            cache_path: Path to the cache file.
            reason: Optional reason for the write failure.
        """
        message = f"Failed to write cache: {cache_path}"
        super().__init__(message, reason)
        self.cache_path = cache_path


class ConfigError(PluginaryError):
    """Base exception for configuration-related errors."""
    pass


class InvalidConfigError(ConfigError):
    """Raised when configuration is invalid."""
    
    def __init__(self, config_key: str, invalid_value: str, reason: Optional[str] = None):
        """Initialize the exception.
        
        Args:
            config_key: Configuration key that has invalid value.
            invalid_value: The invalid value.
            reason: Optional reason why the value is invalid.
        """
        message = f"Invalid configuration value for '{config_key}': {invalid_value}"
        super().__init__(message, reason)
        self.config_key = config_key
        self.invalid_value = invalid_value


class PlatformError(PluginaryError):
    """Raised when an operation is not supported on the current platform."""
    
    def __init__(self, operation: str, platform: str, supported_platforms: Optional[list[str]] = None):
        """Initialize the exception.
        
        Args:
            operation: Operation that is not supported.
            platform: Current platform.
            supported_platforms: Optional list of supported platforms.
        """
        message = f"Operation '{operation}' is not supported on {platform}"
        if supported_platforms:
            details = f"Supported platforms: {', '.join(supported_platforms)}"
        else:
            details = None
        super().__init__(message, details)
        self.operation = operation
        self.platform = platform
        self.supported_platforms = supported_platforms or []