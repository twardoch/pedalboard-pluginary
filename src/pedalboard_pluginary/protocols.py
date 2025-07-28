"""
Protocol definitions for plugin scanner implementations.
"""
from __future__ import annotations

from typing import Protocol, List, Optional, Dict, runtime_checkable
from pathlib import Path

from .models import PluginInfo


@runtime_checkable
class PluginScanner(Protocol):
    """Protocol defining the interface for plugin scanners."""
    
    plugin_type: str
    supported_extensions: List[str]
    
    def find_plugin_files(self, paths: Optional[List[Path]] = None) -> List[Path]:
        """Find all plugin files of this scanner's type.
        
        Args:
            paths: Optional list of specific paths to check. If None, searches default locations.
            
        Returns:
            List of paths to plugin files found.
        """
        ...
    
    def scan_plugin(self, path: Path) -> Optional[PluginInfo]:
        """Scan a single plugin file and return its information.
        
        Args:
            path: Path to the plugin file to scan.
            
        Returns:
            PluginInfo object if successful, None if scanning failed.
        """
        ...
    
    def validate_plugin_path(self, path: Path) -> bool:
        """Validate if a path is a valid plugin for this scanner.
        
        Args:
            path: Path to validate.
            
        Returns:
            True if the path is a valid plugin file, False otherwise.
        """
        ...


@runtime_checkable
class ProgressReporter(Protocol):
    """Protocol for progress reporting implementations."""
    
    def start(self, total: int, description: str = "") -> None:
        """Start progress tracking.
        
        Args:
            total: Total number of items to process.
            description: Optional description of the operation.
        """
        ...
    
    def update(self, amount: int = 1, message: Optional[str] = None) -> None:
        """Update progress.
        
        Args:
            amount: Number of items completed (default: 1).
            message: Optional status message.
        """
        ...
    
    def finish(self, message: Optional[str] = None) -> None:
        """Finish progress tracking.
        
        Args:
            message: Optional completion message.
        """
        ...


@runtime_checkable
class CacheBackend(Protocol):
    """Protocol for cache backend implementations."""
    
    def load(self) -> Dict[str, PluginInfo]:
        """Load all cached plugins.
        
        Returns:
            Dictionary mapping plugin IDs to PluginInfo objects.
        """
        ...
    
    def save(self, plugins: Dict[str, PluginInfo]) -> None:
        """Save plugins to cache.
        
        Args:
            plugins: Dictionary mapping plugin IDs to PluginInfo objects.
        """
        ...
    
    def update(self, plugin_id: str, plugin: PluginInfo) -> None:
        """Update a single plugin in cache.
        
        Args:
            plugin_id: ID of the plugin to update.
            plugin: Updated PluginInfo object.
        """
        ...
    
    def delete(self, plugin_id: str) -> None:
        """Remove a plugin from cache.
        
        Args:
            plugin_id: ID of the plugin to remove.
        """
        ...
    
    def clear(self) -> None:
        """Clear entire cache."""
        ...
    
    def exists(self) -> bool:
        """Check if cache exists.
        
        Returns:
            True if cache exists, False otherwise.
        """
        ...