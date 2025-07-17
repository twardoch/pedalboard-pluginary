# tests/test_exceptions.py
import pytest
from pedalboard_pluginary.exceptions import (
    PluginaryError,
    ScannerError,
    CacheError,
    PluginLoadError,
    TimeoutError,
    ConfigError
)


class TestPluginaryExceptions:
    """Test suite for custom exceptions."""
    
    def test_pluginary_error_basic(self):
        """Test basic PluginaryError."""
        error = PluginaryError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
        
    def test_pluginary_error_with_cause(self):
        """Test PluginaryError with cause."""
        cause = ValueError("Original error")
        error = PluginaryError("Test error", cause)
        assert str(error) == "Test error"
        assert error.cause == cause
        
    def test_scanner_error_inheritance(self):
        """Test ScannerError inherits from PluginaryError."""
        error = ScannerError("Scanner error")
        assert isinstance(error, PluginaryError)
        assert isinstance(error, Exception)
        assert str(error) == "Scanner error"
        
    def test_cache_error_inheritance(self):
        """Test CacheError inherits from PluginaryError."""
        error = CacheError("Cache error")
        assert isinstance(error, PluginaryError)
        assert isinstance(error, Exception)
        assert str(error) == "Cache error"
        
    def test_plugin_load_error_inheritance(self):
        """Test PluginLoadError inherits from ScannerError."""
        error = PluginLoadError("Plugin load error")
        assert isinstance(error, ScannerError)
        assert isinstance(error, PluginaryError)
        assert isinstance(error, Exception)
        assert str(error) == "Plugin load error"
        
    def test_timeout_error_inheritance(self):
        """Test TimeoutError inherits from PluginaryError."""
        error = TimeoutError("Timeout error")
        assert isinstance(error, PluginaryError)
        assert isinstance(error, Exception)
        assert str(error) == "Timeout error"
        
    def test_config_error_inheritance(self):
        """Test ConfigError inherits from PluginaryError."""
        error = ConfigError("Config error")
        assert isinstance(error, PluginaryError)
        assert isinstance(error, Exception)
        assert str(error) == "Config error"
        
    def test_exception_with_details(self):
        """Test exceptions with additional details."""
        plugin_path = "/test/path/plugin.vst3"
        error = PluginLoadError(f"Failed to load plugin: {plugin_path}")
        assert plugin_path in str(error)
        
    def test_exception_chaining(self):
        """Test exception chaining."""
        original_error = FileNotFoundError("File not found")
        
        try:
            raise original_error
        except FileNotFoundError as e:
            cache_error = CacheError("Cache file not found") from e
            assert cache_error.__cause__ == original_error
            
    def test_multiple_error_types(self):
        """Test creating multiple different error types."""
        errors = [
            PluginaryError("Base error"),
            ScannerError("Scanner error"),
            CacheError("Cache error"),
            PluginLoadError("Plugin load error"),
            TimeoutError("Timeout error"),
            ConfigError("Config error")
        ]
        
        for error in errors:
            assert isinstance(error, PluginaryError)
            assert isinstance(error, Exception)
            assert str(error) != ""
            
    def test_error_with_plugin_context(self):
        """Test error with plugin context information."""
        plugin_id = "vst3/TestPlugin"
        plugin_path = "/test/path/TestPlugin.vst3"
        error = PluginLoadError(f"Failed to load plugin {plugin_id} at {plugin_path}")
        
        error_str = str(error)
        assert plugin_id in error_str
        assert plugin_path in error_str
        
    def test_cache_error_scenarios(self):
        """Test various cache error scenarios."""
        cache_errors = [
            CacheError("Cache file corrupted"),
            CacheError("Cache directory not writable"),
            CacheError("Cache version mismatch"),
            CacheError("Cache migration failed")
        ]
        
        for error in cache_errors:
            assert isinstance(error, CacheError)
            assert isinstance(error, PluginaryError)
            
    def test_timeout_error_with_duration(self):
        """Test timeout error with duration information."""
        timeout_duration = 30.0
        error = TimeoutError(f"Operation timed out after {timeout_duration} seconds")
        assert str(timeout_duration) in str(error)
        
    def test_scanner_error_with_scanner_type(self):
        """Test scanner error with scanner type information."""
        scanner_type = "VST3Scanner"
        error = ScannerError(f"{scanner_type} failed to scan plugins")
        assert scanner_type in str(error)