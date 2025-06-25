"""
Unified serialization module for plugin data.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .constants import APP_VERSION, CACHE_VERSION
from .exceptions import CacheCorruptedError, CacheVersionError, CacheWriteError
from .models import PluginInfo, PluginParameter
from .types import (
    CacheData,
    CacheMetadata,
    SerializedParameter,
    SerializedPlugin,
    is_serialized_parameter,
    is_serialized_plugin,
)
from .utils import ensure_folder

logger = logging.getLogger(__name__)


class PluginSerializer:
    """Handles serialization and deserialization of plugin data."""
    
    @staticmethod
    def parameter_to_dict(param: PluginParameter) -> SerializedParameter:
        """Convert PluginParameter to serializable dictionary.
        
        Args:
            param: PluginParameter object to serialize.
            
        Returns:
            SerializedParameter dictionary.
        """
        return {
            "name": param.name,
            "value": param.value,
        }
    
    @staticmethod
    def dict_to_parameter(data: Dict[str, Any]) -> Optional[PluginParameter]:
        """Convert dictionary to PluginParameter with validation.
        
        Args:
            data: Dictionary containing parameter data.
            
        Returns:
            PluginParameter object if valid, None otherwise.
        """
        if not is_serialized_parameter(data):
            logger.warning(f"Invalid parameter data: {data}")
            return None
        
        return PluginParameter(
            name=data["name"],
            value=data["value"],
        )
    
    @staticmethod
    def plugin_to_dict(plugin: PluginInfo) -> SerializedPlugin:
        """Convert PluginInfo to serializable dictionary.
        
        Args:
            plugin: PluginInfo object to serialize.
            
        Returns:
            SerializedPlugin dictionary.
        """
        # Convert parameters
        params_dict: Dict[str, SerializedParameter] = {}
        for param_name, param in plugin.parameters.items():
            params_dict[param_name] = PluginSerializer.parameter_to_dict(param)
        
        result: SerializedPlugin = {
            "id": plugin.id,
            "name": plugin.name,
            "path": plugin.path,
            "filename": plugin.filename,
            "plugin_type": plugin.plugin_type,
            "parameters": params_dict,
        }
        
        # Add optional fields only if they have values
        if plugin.manufacturer is not None:
            result["manufacturer"] = plugin.manufacturer
        if plugin.name_in_file is not None:
            result["name_in_file"] = plugin.name_in_file
        
        return result
    
    @staticmethod
    def dict_to_plugin(data: Dict[str, Any]) -> Optional[PluginInfo]:
        """Convert dictionary to PluginInfo with validation.
        
        Args:
            data: Dictionary containing plugin data.
            
        Returns:
            PluginInfo object if valid, None otherwise.
        """
        if not is_serialized_plugin(data):
            logger.warning(f"Invalid plugin data for ID: {data.get('id', 'unknown')}")
            return None
        
        # Convert parameters
        params: Dict[str, PluginParameter] = {}
        for param_name, param_data in data.get("parameters", {}).items():
            param = PluginSerializer.dict_to_parameter(param_data)
            if param:
                params[param_name] = param
        
        return PluginInfo(
            id=data["id"],
            name=data["name"],
            path=data["path"],
            filename=data["filename"],
            plugin_type=data["plugin_type"],
            parameters=params,
            manufacturer=data.get("manufacturer"),
            name_in_file=data.get("name_in_file"),
        )
    
    @classmethod
    def create_cache_metadata(cls, plugin_count: int) -> CacheMetadata:
        """Create cache metadata.
        
        Args:
            plugin_count: Number of plugins in the cache.
            
        Returns:
            CacheMetadata dictionary.
        """
        now = datetime.utcnow().isoformat()
        return {
            "version": CACHE_VERSION,
            "created_at": now,
            "updated_at": now,
            "plugin_count": plugin_count,
            "scanner_version": APP_VERSION,
        }
    
    @classmethod
    def save_plugins(cls, plugins: Dict[str, PluginInfo], path: Path) -> None:
        """Save plugins to JSON file with metadata and error handling.
        
        Args:
            plugins: Dictionary mapping plugin IDs to PluginInfo objects.
            path: Path to the cache file.
        """
        ensure_folder(path.parent)
        
        # Convert plugins to serializable format
        plugins_dict: Dict[str, SerializedPlugin] = {}
        for plugin_id, plugin in plugins.items():
            try:
                plugins_dict[plugin_id] = cls.plugin_to_dict(plugin)
            except Exception as e:
                logger.error(f"Failed to serialize plugin {plugin_id}: {e}")
                continue
        
        # Create cache data with metadata
        cache_data: CacheData = {
            "metadata": cls.create_cache_metadata(len(plugins_dict)),
            "plugins": plugins_dict,
        }
        
        # Write to file with error handling
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
            logger.info(f"Saved {len(plugins_dict)} plugins to {path}")
        except Exception as e:
            logger.error(f"Failed to save plugins to {path}: {e}")
            raise CacheWriteError(str(path), str(e))
    
    @classmethod
    def load_plugins(cls, path: Path) -> Dict[str, PluginInfo]:
        """Load plugins from JSON file with validation.
        
        Args:
            path: Path to the cache file.
            
        Returns:
            Dictionary mapping plugin IDs to PluginInfo objects.
        """
        if not path.exists():
            logger.info(f"Cache file not found: {path}")
            return {}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in cache file {path}: {e}")
            raise CacheCorruptedError(str(path), f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Failed to read cache file {path}: {e}")
            raise CacheCorruptedError(str(path), str(e))
        
        # Handle both old format (direct plugin dict) and new format (with metadata)
        if isinstance(data, dict) and "metadata" in data and "plugins" in data:
            # New format with metadata
            metadata = data.get("metadata", {})
            cache_version = metadata.get("version", "1.0.0")
            
            if cache_version != CACHE_VERSION:
                logger.warning(f"Cache version mismatch: expected {CACHE_VERSION}, got {cache_version}")
                raise CacheVersionError(CACHE_VERSION, cache_version, str(path))
            
            plugins_data = data.get("plugins", {})
        else:
            # Old format - direct plugin dictionary
            logger.info("Loading cache in legacy format")
            plugins_data = data
        
        # Convert to PluginInfo objects
        plugins: Dict[str, PluginInfo] = {}
        for plugin_id, plugin_data in plugins_data.items():
            if not isinstance(plugin_data, dict):
                logger.warning(f"Invalid plugin data for ID {plugin_id}")
                continue
            
            plugin = cls.dict_to_plugin(plugin_data)
            if plugin:
                plugins[plugin_id] = plugin
            else:
                logger.warning(f"Failed to deserialize plugin {plugin_id}")
        
        logger.info(f"Loaded {len(plugins)} plugins from {path}")
        return plugins
    
    @classmethod
    def migrate_cache(cls, old_data: Dict[str, Any], old_version: str, new_version: str) -> Dict[str, Any]:
        """Migrate cache data from old version to new version.
        
        Args:
            old_data: Cache data in old format.
            old_version: Version of the old cache format.
            new_version: Target version to migrate to.
            
        Returns:
            Migrated cache data.
        """
        # TODO: Implement cache migration logic as needed
        logger.info(f"Migrating cache from version {old_version} to {new_version}")
        return old_data