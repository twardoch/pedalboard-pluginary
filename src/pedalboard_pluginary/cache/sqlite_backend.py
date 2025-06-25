"""SQLite cache backend for high-performance plugin storage."""

import sqlite3
import json
import time
from typing import Dict, Optional, Iterator, List
from pathlib import Path

from ..models import PluginInfo
from ..protocols import CacheBackend
from ..serialization import PluginSerializer
from ..exceptions import CacheError


class SQLiteCacheBackend(CacheBackend):
    """High-performance SQLite cache with indexing and full-text search."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_schema()
    
    def _connect(self) -> sqlite3.Connection:
        """Create database connection with optimizations."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        # Performance optimizations
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")  
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        
        return conn
    
    def _init_schema(self) -> None:
        """Initialize optimized database schema."""
        with self._connect() as conn:
            conn.executescript("""
                -- Main plugins table with optimized indexes
                CREATE TABLE IF NOT EXISTS plugins (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    plugin_type TEXT NOT NULL,
                    manufacturer TEXT,
                    parameter_count INTEGER NOT NULL,
                    data TEXT NOT NULL,  -- JSON blob for full plugin data
                    file_mtime REAL NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                
                -- Performance indexes
                CREATE INDEX IF NOT EXISTS idx_plugins_name ON plugins(name);
                CREATE INDEX IF NOT EXISTS idx_plugins_type ON plugins(plugin_type);
                CREATE INDEX IF NOT EXISTS idx_plugins_manufacturer ON plugins(manufacturer);
                CREATE INDEX IF NOT EXISTS idx_plugins_path ON plugins(path);
                CREATE INDEX IF NOT EXISTS idx_plugins_mtime ON plugins(file_mtime);
                
                -- Full-text search virtual table
                CREATE VIRTUAL TABLE IF NOT EXISTS plugins_fts USING fts5(
                    id UNINDEXED,
                    name,
                    manufacturer,
                    content='plugins',
                    content_rowid='rowid'
                );
                
                -- FTS triggers to keep search index updated
                CREATE TRIGGER IF NOT EXISTS plugins_fts_insert AFTER INSERT ON plugins
                BEGIN
                    INSERT INTO plugins_fts(rowid, id, name, manufacturer)
                    VALUES (new.rowid, new.id, new.name, new.manufacturer);
                END;
                
                CREATE TRIGGER IF NOT EXISTS plugins_fts_delete AFTER DELETE ON plugins
                BEGIN
                    INSERT INTO plugins_fts(plugins_fts, rowid, id, name, manufacturer)
                    VALUES ('delete', old.rowid, old.id, old.name, old.manufacturer);
                END;
                
                CREATE TRIGGER IF NOT EXISTS plugins_fts_update AFTER UPDATE ON plugins
                BEGIN
                    INSERT INTO plugins_fts(plugins_fts, rowid, id, name, manufacturer)
                    VALUES ('delete', old.rowid, old.id, old.name, old.manufacturer);
                    INSERT INTO plugins_fts(rowid, id, name, manufacturer)
                    VALUES (new.rowid, new.id, new.name, new.manufacturer);
                END;
                
                -- Cache metadata table
                CREATE TABLE IF NOT EXISTS cache_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                
                -- Initialize cache version
                INSERT OR IGNORE INTO cache_meta (key, value, updated_at)
                VALUES ('version', '1.0', ?);
            """, (time.time(),))
    
    def load(self) -> Dict[str, PluginInfo]:
        """Load all cached plugins."""
        plugins = {}
        
        try:
            with self._connect() as conn:
                cursor = conn.execute("""
                    SELECT id, data FROM plugins
                    ORDER BY name
                """)
                
                for row in cursor:
                    try:
                        plugin_data = json.loads(row['data'])
                        plugin = PluginSerializer.dict_to_plugin(plugin_data)
                        plugins[row['id']] = plugin
                    except (json.JSONDecodeError, KeyError, TypeError) as e:
                        # Skip corrupted plugin data
                        continue
                        
        except sqlite3.Error as e:
            raise CacheError(f"Failed to load plugins from SQLite cache: {e}")
        
        return plugins
    
    def save(self, plugins: Dict[str, PluginInfo]) -> None:
        """Save plugins to cache."""
        try:
            with self._connect() as conn:
                # Clear existing data
                conn.execute("DELETE FROM plugins")
                
                # Insert all plugins
                current_time = time.time()
                for plugin_id, plugin in plugins.items():
                    self._insert_plugin(conn, plugin_id, plugin, current_time)
                
                conn.commit()
                
        except sqlite3.Error as e:
            raise CacheError(f"Failed to save plugins to SQLite cache: {e}")
    
    def update(self, plugin_id: str, plugin: PluginInfo) -> None:
        """Update a single plugin in cache."""
        try:
            with self._connect() as conn:
                current_time = time.time()
                
                # Check if plugin exists
                cursor = conn.execute("SELECT id FROM plugins WHERE id = ?", (plugin_id,))
                if cursor.fetchone():
                    # Update existing plugin
                    self._update_plugin(conn, plugin_id, plugin, current_time)
                else:
                    # Insert new plugin
                    self._insert_plugin(conn, plugin_id, plugin, current_time)
                
                conn.commit()
                
        except sqlite3.Error as e:
            raise CacheError(f"Failed to update plugin {plugin_id} in SQLite cache: {e}")
    
    def delete(self, plugin_id: str) -> None:
        """Remove a plugin from cache."""
        try:
            with self._connect() as conn:
                conn.execute("DELETE FROM plugins WHERE id = ?", (plugin_id,))
                conn.commit()
                
        except sqlite3.Error as e:
            raise CacheError(f"Failed to delete plugin {plugin_id} from SQLite cache: {e}")
    
    def clear(self) -> None:
        """Clear entire cache."""
        try:
            with self._connect() as conn:
                conn.execute("DELETE FROM plugins")
                conn.commit()
                
        except sqlite3.Error as e:
            raise CacheError(f"Failed to clear SQLite cache: {e}")
    
    def exists(self) -> bool:
        """Check if cache exists."""
        return self.db_path.exists()
    
    def search(self, query: str, limit: int = 50) -> List[PluginInfo]:
        """Full-text search for plugins."""
        plugins = []
        
        try:
            with self._connect() as conn:
                cursor = conn.execute("""
                    SELECT p.id, p.data 
                    FROM plugins p
                    JOIN plugins_fts fts ON p.rowid = fts.rowid
                    WHERE plugins_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, limit))
                
                for row in cursor:
                    try:
                        plugin_data = json.loads(row['data'])
                        plugin = PluginSerializer.dict_to_plugin(plugin_data)
                        plugins.append(plugin)
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue
                        
        except sqlite3.Error as e:
            raise CacheError(f"Failed to search plugins: {e}")
        
        return plugins
    
    def filter_by_type(self, plugin_type: str) -> List[PluginInfo]:
        """Filter plugins by type."""
        plugins = []
        
        try:
            with self._connect() as conn:
                cursor = conn.execute("""
                    SELECT id, data FROM plugins
                    WHERE plugin_type = ?
                    ORDER BY name
                """, (plugin_type,))
                
                for row in cursor:
                    try:
                        plugin_data = json.loads(row['data'])
                        plugin = PluginSerializer.dict_to_plugin(plugin_data)
                        plugins.append(plugin)
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue
                        
        except sqlite3.Error as e:
            raise CacheError(f"Failed to filter plugins by type: {e}")
        
        return plugins
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        stats = {}
        
        try:
            with self._connect() as conn:
                # Total plugin count
                cursor = conn.execute("SELECT COUNT(*) as count FROM plugins")
                stats['total_plugins'] = cursor.fetchone()['count']
                
                # Plugin counts by type
                cursor = conn.execute("""
                    SELECT plugin_type, COUNT(*) as count 
                    FROM plugins 
                    GROUP BY plugin_type
                """)
                for row in cursor:
                    stats[f"{row['plugin_type']}_plugins"] = row['count']
                
                # Database size
                cursor = conn.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                stats['db_size_bytes'] = cursor.fetchone()['size']
                
        except sqlite3.Error as e:
            raise CacheError(f"Failed to get cache stats: {e}")
        
        return stats
    
    def _insert_plugin(self, conn: sqlite3.Connection, plugin_id: str, plugin: PluginInfo, current_time: float) -> None:
        """Insert a plugin into the database."""
        plugin_data = PluginSerializer.plugin_to_dict(plugin)
        
        conn.execute("""
            INSERT INTO plugins (
                id, name, path, plugin_type, manufacturer, parameter_count,
                data, file_mtime, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plugin_id,
            plugin.name,
            str(plugin.path),
            plugin.plugin_type,
            plugin.manufacturer,
            len(plugin.parameters),
            json.dumps(plugin_data),
            plugin.path.stat().st_mtime if plugin.path.exists() else 0,
            current_time,
            current_time
        ))
    
    def _update_plugin(self, conn: sqlite3.Connection, plugin_id: str, plugin: PluginInfo, current_time: float) -> None:
        """Update an existing plugin in the database."""
        plugin_data = PluginSerializer.plugin_to_dict(plugin)
        
        conn.execute("""
            UPDATE plugins SET
                name = ?, path = ?, plugin_type = ?, manufacturer = ?,
                parameter_count = ?, data = ?, file_mtime = ?, updated_at = ?
            WHERE id = ?
        """, (
            plugin.name,
            str(plugin.path),
            plugin.plugin_type,
            plugin.manufacturer,
            len(plugin.parameters),
            json.dumps(plugin_data),
            plugin.path.stat().st_mtime if plugin.path.exists() else 0,
            current_time,
            plugin_id
        ))