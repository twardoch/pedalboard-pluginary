"""Migration utilities for cache backends."""

import logging
from pathlib import Path

from ..models import PluginInfo
from .json_backend import JSONCacheBackend
from .sqlite_backend import SQLiteCacheBackend

logger = logging.getLogger(__name__)


def migrate_json_to_sqlite(json_path: Path, sqlite_path: Path) -> int:
    """Migrate plugins from JSON cache to SQLite cache.
    
    Args:
        json_path: Path to existing JSON cache file.
        sqlite_path: Path to new SQLite cache database.
        
    Returns:
        Number of plugins migrated.
        
    Raises:
        FileNotFoundError: If JSON cache doesn't exist.
        Exception: If migration fails.
    """
    if not json_path.exists():
        raise FileNotFoundError(f"JSON cache not found: {json_path}")
    
    logger.info(f"Migrating plugins from {json_path} to {sqlite_path}")
    
    # Load from JSON
    json_backend = JSONCacheBackend(json_path)
    plugins = json_backend.load()
    
    if not plugins:
        logger.warning("No plugins found in JSON cache")
        return 0
    
    # Save to SQLite
    sqlite_backend = SQLiteCacheBackend(sqlite_path)
    sqlite_backend.save(plugins)
    
    plugin_count = len(plugins)
    logger.info(f"Successfully migrated {plugin_count} plugins to SQLite cache")
    
    return plugin_count


def backup_json_cache(json_path: Path, backup_suffix: str = ".backup") -> Path:
    """Create a backup of the JSON cache before migration.
    
    Args:
        json_path: Path to JSON cache file.
        backup_suffix: Suffix to add to backup filename.
        
    Returns:
        Path to backup file.
    """
    if not json_path.exists():
        raise FileNotFoundError(f"JSON cache not found: {json_path}")
    
    backup_path = json_path.with_suffix(json_path.suffix + backup_suffix)
    backup_path.write_bytes(json_path.read_bytes())
    
    logger.info(f"Created backup: {backup_path}")
    return backup_path