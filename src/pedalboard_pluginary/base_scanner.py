"""
Base scanner class implementing common functionality for all plugin scanners.
"""

import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from .models import PluginInfo
from .protocols import PluginScanner

logger = logging.getLogger(__name__)


class BaseScanner(ABC):
    """Base class for plugin scanner implementations."""
    
    def __init__(
        self,
        ignore_paths: Optional[List[str]] = None,
        specific_paths: Optional[List[str]] = None,
    ):
        """Initialize the scanner with optional ignore paths and specific paths.
        
        Args:
            ignore_paths: List of regex patterns for paths to ignore.
            specific_paths: List of specific paths to scan (if provided, only these are scanned).
        """
        self.ignore_paths = ignore_paths or []
        self.specific_paths = specific_paths or []
        self._compiled_ignore_patterns = [re.compile(pattern) for pattern in self.ignore_paths]
    
    @property
    @abstractmethod
    def plugin_type(self) -> str:
        """Return the plugin type this scanner handles (e.g., 'vst3', 'aufx')."""
        ...
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return list of file extensions this scanner supports."""
        ...
    
    @abstractmethod
    def find_plugin_files(self, paths: Optional[List[Path]] = None) -> List[Path]:
        """Find all plugin files of this scanner's type.
        
        Args:
            paths: Optional list of specific paths to check.
            
        Returns:
            List of paths to plugin files found.
        """
        ...
    
    @abstractmethod
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
        if not path.exists():
            return False
        
        # Check extension
        if path.suffix not in self.supported_extensions:
            return False
        
        # Check against ignore patterns
        if self._should_ignore_path(path):
            return False
        
        # Check if specific paths are set and this path is in them
        if self.specific_paths and str(path) not in self.specific_paths:
            return False
        
        return True
    
    def _should_ignore_path(self, path: Path) -> bool:
        """Check if a path should be ignored based on ignore patterns.
        
        Args:
            path: Path to check.
            
        Returns:
            True if the path should be ignored, False otherwise.
        """
        path_str = str(path)
        for pattern in self._compiled_ignore_patterns:
            if pattern.search(path_str):
                logger.debug(f"Ignoring path {path} due to pattern {pattern.pattern}")
                return True
        return False
    
    def _filter_plugin_paths(self, paths: List[Path]) -> List[Path]:
        """Filter plugin paths based on validation criteria.
        
        Args:
            paths: List of paths to filter.
            
        Returns:
            Filtered list of valid plugin paths.
        """
        valid_paths = []
        for path in paths:
            if self.validate_plugin_path(path):
                valid_paths.append(path)
            else:
                logger.debug(f"Filtered out invalid plugin path: {path}")
        
        return valid_paths
    
    def _create_plugin_id(self, path: Path) -> str:
        """Create a unique plugin ID from its path.
        
        Args:
            path: Path to the plugin.
            
        Returns:
            Unique plugin ID string.
        """
        return f"{self.plugin_type}/{path.stem}"