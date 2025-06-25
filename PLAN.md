# Pedalboard Pluginary - Production Readiness Implementation Plan

## Executive Summary

Based on comprehensive codebase analysis, Pedalboard Pluginary has achieved **exceptional async infrastructure** and **enterprise-grade type safety**. The async scanner implementation provides foundation for 10x performance improvements. Current focus must shift to **SQLite scalability**, **modern CLI experience**, and **production features** to complete the transformation into a high-performance, professional-grade tool.

## Current State Assessment

### ✅ **Major Achievements Completed**

**Async Performance Infrastructure (100% Complete)**
- AsyncScannerMixin with semaphore-based concurrency control
- Full integration in VST3Scanner and AUScanner classes  
- PedalboardScanner async methods (full_scan_async, update_scan_async)
- Configurable concurrency limits (1-50 concurrent scans)
- Progress reporting integration with real-time feedback

**Type Safety Excellence (100% Complete)**
- Zero mypy errors in strict mode across entire codebase
- Comprehensive protocol-based architecture
- Complete TypedDict definitions for serialization
- Robust custom exception hierarchy

**Foundation Infrastructure (100% Complete)**
- Timeout protection with sync_timeout and async_timeout
- Retry logic with exponential backoff
- Multiple progress reporter implementations
- Unified serialization layer with validation

### 🎯 **Critical Gaps Requiring Immediate Action**

**Performance Scalability Crisis**
- JSON cache becomes bottleneck at 500+ plugins (O(n) operations)
- No indexed search capabilities
- Missing lazy loading for large datasets
- Full rescans required (no incremental updates)

**User Experience Deficiencies**
- Outdated Fire-based CLI with poor error handling
- No search/filtering capabilities
- Missing rich output formatting
- No comprehensive help system

**Production Readiness Gaps**
- No configuration management system
- Missing health monitoring and error recovery
- No automated testing for async functionality
- Basic cache management without repair capabilities

## Phase 1: SQLite Cache Backend Revolution (Days 1-5)

### 1.1 Core SQLite Implementation

**Problem**: JSON cache hits performance wall at ~500 plugins with O(n) operations.

**Solution**: SQLite backend with indexing, FTS, and lazy loading.

```python
# src/pedalboard_pluginary/cache/__init__.py
from .sqlite_backend import SQLiteCacheBackend
from .json_backend import JSONCacheBackend  # Legacy compatibility
from .migration import migrate_json_to_sqlite

# src/pedalboard_pluginary/cache/sqlite_backend.py
import sqlite3
import json
from typing import Dict, Optional, Iterator, List
from pathlib import Path
from ..models import PluginInfo
from ..protocols import CacheBackend

class SQLiteCacheBackend(CacheBackend):
    """High-performance SQLite cache with indexing and FTS."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_schema()
    
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
                CREATE INDEX IF NOT EXISTS idx_plugins_param_count ON plugins(parameter_count);
                
                -- Full-text search for names and manufacturers
                CREATE VIRTUAL TABLE IF NOT EXISTS plugins_fts USING fts5(
                    id UNINDEXED,
                    name,
                    manufacturer,
                    content='plugins',
                    content_rowid='rowid'
                );
                
                -- FTS triggers for automatic index maintenance
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
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                
                -- Insert initial metadata
                INSERT OR IGNORE INTO cache_metadata (key, value, updated_at)
                VALUES 
                    ('version', '2.0.0', strftime('%s', 'now')),
                    ('created_at', strftime('%s', 'now'), strftime('%s', 'now'));
            """)
    
    def get(self, plugin_id: str) -> Optional[PluginInfo]:
        """Get single plugin without loading entire cache."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM plugins WHERE id = ?", 
                (plugin_id,)
            ).fetchone()
            
            if row:
                data = json.loads(row[0])
                return PluginSerializer.dict_to_plugin(data)
            return None
    
    def search(
        self,
        query: Optional[str] = None,
        plugin_type: Optional[str] = None,
        manufacturer: Optional[str] = None,
        parameter_count_range: Optional[tuple] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Iterator[PluginInfo]:
        """Advanced search with multiple filters and pagination."""
        conditions = []
        params = []
        
        # Full-text search
        if query:
            conditions.append("""
                id IN (
                    SELECT id FROM plugins_fts 
                    WHERE plugins_fts MATCH ?
                )
            """)
            params.append(query)
        
        # Type filter
        if plugin_type:
            conditions.append("plugin_type = ?")
            params.append(plugin_type)
        
        # Manufacturer filter (supports partial matching)
        if manufacturer:
            conditions.append("manufacturer LIKE ?")
            params.append(f"%{manufacturer}%")
        
        # Parameter count range
        if parameter_count_range:
            min_params, max_params = parameter_count_range
            conditions.append("parameter_count BETWEEN ? AND ?")
            params.extend([min_params, max_params])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
            SELECT data FROM plugins 
            WHERE {where_clause}
            ORDER BY name COLLATE NOCASE
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        with self._connect() as conn:
            for row in conn.execute(sql, params):
                data = json.loads(row[0])
                plugin = PluginSerializer.dict_to_plugin(data)
                if plugin:
                    yield plugin
    
    def save(self, plugins: Dict[str, PluginInfo]) -> None:
        """Efficiently save plugins with transaction."""
        import time
        
        with self._connect() as conn:
            conn.execute("BEGIN TRANSACTION")
            try:
                for plugin_id, plugin in plugins.items():
                    data = PluginSerializer.plugin_to_dict(plugin)
                    
                    # Get file modification time
                    file_mtime = 0
                    try:
                        file_mtime = Path(plugin.path).stat().st_mtime
                    except (OSError, ValueError):
                        pass  # File might not exist or be invalid
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO plugins 
                        (id, name, path, plugin_type, manufacturer, parameter_count,
                         data, file_mtime, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 
                               COALESCE((SELECT created_at FROM plugins WHERE id = ?), ?),
                               ?)
                    """, (
                        plugin_id,
                        plugin.name,
                        plugin.path,
                        plugin.plugin_type,
                        plugin.manufacturer,
                        len(plugin.parameters),
                        json.dumps(data),
                        file_mtime,
                        plugin_id,  # For COALESCE lookup
                        time.time(),  # created_at if new
                        time.time()   # updated_at
                    ))
                
                conn.execute("COMMIT")
                
                # Update cache metadata
                conn.execute("""
                    UPDATE cache_metadata 
                    SET value = ?, updated_at = ?
                    WHERE key = 'last_updated'
                """, (str(time.time()), time.time()))
                
            except Exception:
                conn.execute("ROLLBACK")
                raise
    
    def delete(self, plugin_id: str) -> None:
        """Delete plugin efficiently."""
        with self._connect() as conn:
            conn.execute("DELETE FROM plugins WHERE id = ?", (plugin_id,))
    
    def clear(self) -> None:
        """Clear all plugins efficiently."""
        with self._connect() as conn:
            conn.execute("DELETE FROM plugins")
            # FTS table will be automatically updated by triggers
    
    def exists(self) -> bool:
        """Check if cache exists and has plugins."""
        if not self.db_path.exists():
            return False
        
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM plugins").fetchone()[0]
            return count > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        with self._connect() as conn:
            # Total count
            total = conn.execute("SELECT COUNT(*) FROM plugins").fetchone()[0]
            
            # By type
            type_stats = {}
            for row in conn.execute("""
                SELECT plugin_type, COUNT(*) 
                FROM plugins 
                GROUP BY plugin_type
            """):
                type_stats[row[0]] = row[1]
            
            # By manufacturer (top 10)
            manufacturer_stats = {}
            for row in conn.execute("""
                SELECT manufacturer, COUNT(*) 
                FROM plugins 
                WHERE manufacturer IS NOT NULL
                GROUP BY manufacturer 
                ORDER BY COUNT(*) DESC 
                LIMIT 10
            """):
                manufacturer_stats[row[0]] = row[1]
            
            # Database size
            db_size = 0
            if self.db_path.exists():
                db_size = self.db_path.stat().st_size
            
            # Last updated
            last_updated = conn.execute("""
                SELECT value FROM cache_metadata 
                WHERE key = 'last_updated'
            """).fetchone()
            
            return {
                "total_plugins": total,
                "by_type": type_stats,
                "top_manufacturers": manufacturer_stats,
                "database_size_bytes": db_size,
                "last_updated": last_updated[0] if last_updated else None
            }
    
    def get_changed_plugins(self, since_mtime: float) -> List[str]:
        """Get plugins that have changed since given modification time."""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT id FROM plugins 
                WHERE file_mtime > ?
                ORDER BY file_mtime DESC
            """, (since_mtime,)).fetchall()
            
            return [row[0] for row in rows]
    
    def vacuum(self) -> None:
        """Optimize database performance."""
        with self._connect() as conn:
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
    
    def _connect(self) -> sqlite3.Connection:
        """Create optimized database connection."""
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        
        # Performance optimizations
        conn.execute("PRAGMA journal_mode=WAL")        # Better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")      # Balance safety/speed
        conn.execute("PRAGMA cache_size=-64000")       # 64MB cache
        conn.execute("PRAGMA temp_store=MEMORY")       # Memory temp tables
        conn.execute("PRAGMA mmap_size=268435456")     # 256MB memory mapping
        
        return conn
```

**Implementation Steps**:
1. Create cache package structure
2. Implement SQLiteCacheBackend with schema and indexes
3. Add comprehensive search capabilities with FTS
4. Create migration utility from JSON to SQLite
5. Add cache statistics and management methods

**Expected Impact**:
- **Search Performance**: O(log n) vs O(n) - 100x improvement for large datasets
- **Memory Usage**: Constant vs linear - handle unlimited plugin counts
- **Query Capabilities**: Full-text search, filtering, sorting, pagination
- **Scalability**: Handle 10,000+ plugins efficiently

### 1.2 JSON to SQLite Migration

```python
# src/pedalboard_pluginary/cache/migration.py
import logging
from pathlib import Path
from typing import Dict
from ..data import load_json_file
from ..models import PluginInfo
from ..serialization import PluginSerializer
from .sqlite_backend import SQLiteCacheBackend

logger = logging.getLogger(__name__)

class CacheMigration:
    """Handles migration from JSON to SQLite cache."""
    
    @staticmethod
    def migrate_json_to_sqlite(
        json_path: Path, 
        sqlite_path: Path,
        backup: bool = True
    ) -> bool:
        """Migrate existing JSON cache to SQLite format."""
        if not json_path.exists():
            logger.info("No JSON cache found, starting with empty SQLite cache")
            return True
        
        # Backup existing JSON if requested
        if backup:
            backup_path = json_path.with_suffix('.json.backup')
            backup_path.write_bytes(json_path.read_bytes())
            logger.info(f"JSON cache backed up to {backup_path}")
        
        try:
            # Load existing JSON data
            json_data = load_json_file(json_path)
            if not json_data:
                logger.info("Empty JSON cache, starting fresh")
                return True
            
            # Convert to PluginInfo objects
            plugins: Dict[str, PluginInfo] = {}
            for plugin_id, plugin_data in json_data.items():
                plugin = PluginSerializer.dict_to_plugin(plugin_data)
                if plugin:
                    plugins[plugin_id] = plugin
                else:
                    logger.warning(f"Failed to migrate plugin: {plugin_id}")
            
            # Save to SQLite
            sqlite_backend = SQLiteCacheBackend(sqlite_path)
            sqlite_backend.save(plugins)
            
            logger.info(f"Successfully migrated {len(plugins)} plugins to SQLite")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    @staticmethod
    def verify_migration(json_path: Path, sqlite_path: Path) -> bool:
        """Verify migration completed successfully."""
        if not json_path.exists() or not sqlite_path.exists():
            return False
        
        try:
            # Count JSON plugins
            json_data = load_json_file(json_path)
            json_count = len(json_data) if json_data else 0
            
            # Count SQLite plugins
            sqlite_backend = SQLiteCacheBackend(sqlite_path)
            sqlite_stats = sqlite_backend.get_stats()
            sqlite_count = sqlite_stats["total_plugins"]
            
            return json_count == sqlite_count
            
        except Exception as e:
            logger.error(f"Migration verification failed: {e}")
            return False
```

### 1.3 Cache Backend Factory

```python
# src/pedalboard_pluginary/cache/factory.py
from pathlib import Path
from typing import Union
from ..protocols import CacheBackend
from .sqlite_backend import SQLiteCacheBackend
from .json_backend import JSONCacheBackend
from .migration import CacheMigration

def create_cache_backend(
    backend_type: str,
    cache_dir: Path,
    auto_migrate: bool = True
) -> CacheBackend:
    """Factory for creating cache backends with automatic migration."""
    
    if backend_type == "sqlite":
        sqlite_path = cache_dir / "plugins.db"
        json_path = cache_dir / "plugins.json"
        
        # Auto-migrate from JSON if needed
        if auto_migrate and json_path.exists() and not sqlite_path.exists():
            CacheMigration.migrate_json_to_sqlite(json_path, sqlite_path)
        
        return SQLiteCacheBackend(sqlite_path)
    
    elif backend_type == "json":
        return JSONCacheBackend(cache_dir / "plugins.json")
    
    else:
        raise ValueError(f"Unknown cache backend: {backend_type}")
```

## Phase 2: Modern CLI Revolution (Days 6-10)

### 2.1 Click Framework Migration

**Problem**: Fire-based CLI lacks modern features, poor error handling, no help system.

**Solution**: Complete migration to Click with Rich formatting.

```python
# src/pedalboard_pluginary/cli.py
import asyncio
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.prompt import Confirm

from .core import PedalboardPluginary
from .models import PluginInfo
from .constants import DEFAULT_MAX_CONCURRENT

console = Console()

@click.group()
@click.version_option()
@click.option('--config-file', type=click.Path(exists=True), help='Configuration file path')
@click.option('--cache-dir', type=click.Path(), help='Cache directory override')
@click.option('--verbose', '-v', count=True, help='Increase verbosity (-v, -vv, -vvv)')
@click.pass_context
def cli(ctx: click.Context, config_file: Optional[str], cache_dir: Optional[str], verbose: int):
    """Pedalboard Pluginary - Professional audio plugin scanner and manager.
    
    Discover, catalog, and manage VST3 and Audio Unit plugins on your system
    with lightning-fast async scanning and powerful search capabilities.
    
    Examples:
        pbpluginary scan --async                    # Fast async plugin scan
        pbpluginary list --filter "reverb"         # Find reverb plugins  
        pbpluginary search "FabFilter" --type vst3 # Search FabFilter VST3s
        pbpluginary info "vst3/Pro-Q 3"           # Detailed plugin info
    """
    # Store context for subcommands
    ctx.ensure_object(dict)
    ctx.obj['config_file'] = config_file
    ctx.obj['cache_dir'] = Path(cache_dir) if cache_dir else None
    ctx.obj['verbose'] = verbose
    
    # Setup logging based on verbosity
    setup_logging(verbose)

@cli.command()
@click.option('--async/--sync', 'async_mode', default=True, 
              help='Use async scanning for better performance (default: async)')
@click.option('--concurrency', default=DEFAULT_MAX_CONCURRENT, 
              help=f'Max concurrent scans in async mode (default: {DEFAULT_MAX_CONCURRENT})')
@click.option('--timeout', default=10.0, 
              help='Plugin load timeout in seconds (default: 10.0)')
@click.option('--folders', help='Additional folders to scan (comma-separated)')
@click.option('--force', is_flag=True, 
              help='Force full rescan (ignore existing cache)')
@click.option('--cache-backend', type=click.Choice(['sqlite', 'json']), default='sqlite',
              help='Cache backend to use (default: sqlite)')
@click.pass_context
def scan(ctx: click.Context, async_mode: bool, concurrency: int, timeout: float, 
         folders: Optional[str], force: bool, cache_backend: str):
    """Scan system for audio plugins with high-performance async processing.
    
    Discovers VST3 and Audio Unit plugins in standard system locations
    and any additional folders specified. Results are cached for fast
    subsequent operations.
    
    Examples:
        pbpluginary scan                            # Quick async scan
        pbpluginary scan --sync                     # Synchronous scan
        pbpluginary scan --folders ~/MyPlugins      # Include custom folder
        pbpluginary scan --force                    # Rebuild entire cache
        pbpluginary scan --concurrency 20          # Higher concurrency
    """
    extra_folders = [Path(f.strip()) for f in folders.split(',')] if folders else []
    
    # Initialize scanner
    try:
        scanner = PedalboardPluginary(
            cache_dir=ctx.obj['cache_dir'],
            async_mode=async_mode,
            max_concurrent=concurrency,
            timeout=timeout,
            cache_backend=cache_backend
        )
    except Exception as e:
        console.print(f"[red]Failed to initialize scanner: {e}[/red]")
        raise click.Abort()
    
    # Clear cache if force requested
    if force:
        if scanner.cache_exists():
            if Confirm.ask("Clear existing cache and perform full rescan?"):
                scanner.clear_cache()
                console.print("[yellow]Cache cleared[/yellow]")
            else:
                console.print("[yellow]Scan cancelled[/yellow]")
                return
    
    # Perform scan with progress
    scan_start_time = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        def progress_callback(current: int, total: int, message: str = ""):
            if not hasattr(progress_callback, 'task_id'):
                progress_callback.task_id = progress.add_task("Scanning...", total=total)
            
            progress.update(
                progress_callback.task_id, 
                completed=current, 
                total=total,
                description=f"Scanning plugins... {message}"
            )
        
        try:
            if async_mode:
                plugins = asyncio.run(scanner.scan_async(
                    extra_folders=extra_folders,
                    progress_callback=progress_callback
                ))
            else:
                plugins = scanner.scan(
                    extra_folders=extra_folders,
                    progress_callback=progress_callback
                )
        except KeyboardInterrupt:
            console.print("\n[yellow]Scan interrupted by user[/yellow]")
            return
        except Exception as e:
            console.print(f"\n[red]Scan failed: {e}[/red]")
            raise click.Abort()
    
    scan_duration = time.time() - scan_start_time
    
    # Display results summary
    _display_scan_results(plugins, scan_duration, async_mode)

@cli.command('list')
@click.option('--format', type=click.Choice(['table', 'json', 'yaml', 'csv']), 
              default='table', help='Output format (default: table)')
@click.option('--filter', 'filter_text', help='Filter plugins by name or manufacturer')
@click.option('--type', 'plugin_type', type=click.Choice(['vst3', 'au']), 
              help='Filter by plugin type')
@click.option('--manufacturer', help='Filter by manufacturer')
@click.option('--parameters', help='Filter by parameter count (e.g., "10-50", ">20", "<10")')
@click.option('--sort', type=click.Choice(['name', 'type', 'manufacturer', 'parameters']),
              default='name', help='Sort by field (default: name)')
@click.option('--reverse', is_flag=True, help='Reverse sort order')
@click.option('--limit', default=50, help='Limit number of results (default: 50)')
@click.option('--offset', default=0, help='Skip first N results (default: 0)')
@click.pass_context
def list_plugins(ctx: click.Context, format: str, filter_text: Optional[str], 
                plugin_type: Optional[str], manufacturer: Optional[str],
                parameters: Optional[str], sort: str, reverse: bool,
                limit: int, offset: int):
    """List discovered plugins with advanced filtering and formatting.
    
    Display plugins in various formats with powerful filtering capabilities.
    Supports full-text search, type filtering, and parameter-based queries.
    
    Examples:
        pbpluginary list                            # Show all plugins (table)
        pbpluginary list --filter "reverb"         # Search for reverb plugins
        pbpluginary list --type vst3 --format json # VST3 plugins as JSON
        pbpluginary list --manufacturer FabFilter   # FabFilter plugins only
        pbpluginary list --parameters ">50"        # Plugins with 50+ parameters
        pbpluginary list --sort manufacturer       # Sort by manufacturer
    """
    try:
        scanner = PedalboardPluginary(cache_dir=ctx.obj['cache_dir'])
        
        # Parse parameter filter
        param_range = None
        if parameters:
            param_range = _parse_parameter_filter(parameters)
        
        # Search plugins
        plugins = list(scanner.search_plugins(
            query=filter_text,
            plugin_type=plugin_type,
            manufacturer=manufacturer,
            parameter_count_range=param_range,
            sort_by=sort,
            sort_desc=reverse,
            limit=limit,
            offset=offset
        ))
        
        if not plugins:
            console.print("[yellow]No plugins found matching criteria[/yellow]")
            return
        
        # Output results
        _output_plugins(plugins, format)
        
        # Show pagination info
        if len(plugins) == limit:
            console.print(f"\n[dim]Showing results {offset + 1}-{offset + len(plugins)}. "
                         f"Use --offset {offset + limit} to see more.[/dim]")
        
    except Exception as e:
        console.print(f"[red]Failed to list plugins: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.argument('query')
@click.option('--type', 'plugin_type', type=click.Choice(['vst3', 'au']), 
              help='Filter by plugin type')
@click.option('--fuzzy', is_flag=True, help='Enable fuzzy matching')
@click.option('--limit', default=20, help='Limit number of results (default: 20)')
@click.pass_context
def search(ctx: click.Context, query: str, plugin_type: Optional[str], 
           fuzzy: bool, limit: int):
    """Search plugins with full-text search and fuzzy matching.
    
    Performs advanced search across plugin names, manufacturers, and metadata.
    Supports exact matching and fuzzy search for approximate results.
    
    Examples:
        pbpluginary search "Pro-Q"                  # Exact search
        pbpluginary search "compressor" --fuzzy     # Fuzzy search
        pbpluginary search "reverb" --type vst3     # Type-filtered search
    """
    try:
        scanner = PedalboardPluginary(cache_dir=ctx.obj['cache_dir'])
        
        if fuzzy:
            plugins = scanner.fuzzy_search(query, limit=limit)
        else:
            plugins = list(scanner.search_plugins(
                query=query,
                plugin_type=plugin_type,
                limit=limit
            ))
        
        if not plugins:
            console.print(f"[yellow]No plugins found for '{query}'[/yellow]")
            if not fuzzy:
                console.print("[dim]Try --fuzzy for approximate matching[/dim]")
            return
        
        # Display as table with relevance scores for fuzzy search
        _output_search_results(plugins, query, fuzzy)
        
    except Exception as e:
        console.print(f"[red]Search failed: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.argument('plugin_id')
@click.option('--parameters/--no-parameters', default=True, 
              help='Show plugin parameters (default: show)')
@click.option('--test', is_flag=True, help='Test plugin loading')
@click.option('--suggest', is_flag=True, help='Show similar plugins')
@click.pass_context
def info(ctx: click.Context, plugin_id: str, parameters: bool, test: bool, suggest: bool):
    """Show detailed information about a specific plugin.
    
    Display comprehensive plugin information including metadata,
    parameters, and optionally test plugin loading capabilities.
    
    Examples:
        pbpluginary info "vst3/FabFilter Pro-Q 3"   # Basic plugin info
        pbpluginary info "au/ChromaVerb" --test     # Test loading
        pbpluginary info "vst3/Reverb" --suggest    # Show similar plugins
    """
    try:
        scanner = PedalboardPluginary(cache_dir=ctx.obj['cache_dir'])
        plugin = scanner.get_plugin(plugin_id)
        
        if not plugin:
            console.print(f"[red]Plugin '{plugin_id}' not found[/red]")
            # Try fuzzy search for suggestions
            suggestions = scanner.fuzzy_search(plugin_id, limit=5)
            if suggestions:
                console.print("\n[yellow]Did you mean one of these?[/yellow]")
                for suggestion in suggestions:
                    console.print(f"  {suggestion.id}")
            raise click.Abort()
        
        # Display plugin information
        _display_plugin_info(plugin, parameters, test)
        
        # Show similar plugins if requested
        if suggest:
            similar = scanner.suggest_similar(plugin_id, limit=5)
            if similar:
                console.print("\n[bold]Similar Plugins:[/bold]")
                _output_plugins(similar, 'table')
        
    except Exception as e:
        console.print(f"[red]Failed to get plugin info: {e}[/red]")
        raise click.Abort()

# Cache management subcommands
@cli.group()
def cache():
    """Cache management commands."""
    pass

@cache.command()
@click.pass_context
def stats(ctx: click.Context):
    """Show detailed cache statistics and health information."""
    try:
        scanner = PedalboardPluginary(cache_dir=ctx.obj['cache_dir'])
        stats = scanner.get_cache_stats()
        
        _display_cache_stats(stats)
        
    except Exception as e:
        console.print(f"[red]Failed to get cache stats: {e}[/red]")
        raise click.Abort()

@cache.command()
@click.option('--backup/--no-backup', default=True, 
              help='Backup cache before clearing (default: backup)')
@click.pass_context
def clear(ctx: click.Context, backup: bool):
    """Clear the plugin cache with optional backup."""
    try:
        scanner = PedalboardPluginary(cache_dir=ctx.obj['cache_dir'])
        
        if not scanner.cache_exists():
            console.print("[yellow]No cache found to clear[/yellow]")
            return
        
        stats = scanner.get_cache_stats()
        plugin_count = stats.get('total_plugins', 0)
        
        if not Confirm.ask(f"Clear cache containing {plugin_count} plugins?"):
            console.print("[yellow]Cache clear cancelled[/yellow]")
            return
        
        if backup:
            backup_path = scanner.backup_cache()
            console.print(f"[green]Cache backed up to {backup_path}[/green]")
        
        scanner.clear_cache()
        console.print("[green]Cache cleared successfully[/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to clear cache: {e}[/red]")
        raise click.Abort()

@cache.command()
@click.pass_context
def repair(ctx: click.Context):
    """Repair corrupted cache and validate integrity."""
    try:
        scanner = PedalboardPluginary(cache_dir=ctx.obj['cache_dir'])
        
        with console.status("Analyzing cache integrity..."):
            issues = scanner.validate_cache()
        
        if not issues:
            console.print("[green]Cache is healthy - no issues found[/green]")
            return
        
        console.print(f"[yellow]Found {len(issues)} cache issues:[/yellow]")
        for issue in issues:
            console.print(f"  • {issue}")
        
        if Confirm.ask("Attempt to repair cache?"):
            with console.status("Repairing cache..."):
                repaired = scanner.repair_cache()
            
            if repaired:
                console.print("[green]Cache repaired successfully[/green]")
            else:
                console.print("[red]Cache repair failed[/red]")
        
    except Exception as e:
        console.print(f"[red]Cache repair failed: {e}[/red]")
        raise click.Abort()

@cache.command()
@click.option('--to', type=click.Choice(['sqlite', 'json']), required=True,
              help='Target cache backend')
@click.option('--backup/--no-backup', default=True,
              help='Backup original cache (default: backup)')
@click.pass_context
def migrate(ctx: click.Context, to: str, backup: bool):
    """Migrate cache between different backend formats."""
    try:
        scanner = PedalboardPluginary(cache_dir=ctx.obj['cache_dir'])
        
        with console.status(f"Migrating cache to {to} format..."):
            success = scanner.migrate_cache(to, backup=backup)
        
        if success:
            console.print(f"[green]Successfully migrated cache to {to} format[/green]")
        else:
            console.print(f"[red]Cache migration to {to} failed[/red]")
        
    except Exception as e:
        console.print(f"[red]Migration failed: {e}[/red]")
        raise click.Abort()

# Utility functions for CLI formatting
def _display_scan_results(plugins: Dict[str, PluginInfo], duration: float, async_mode: bool):
    """Display scan results with Rich formatting."""
    # Summary statistics
    type_counts = {}
    manufacturer_counts = {}
    
    for plugin in plugins.values():
        type_counts[plugin.plugin_type] = type_counts.get(plugin.plugin_type, 0) + 1
        if plugin.manufacturer:
            manufacturer_counts[plugin.manufacturer] = manufacturer_counts.get(plugin.manufacturer, 0) + 1
    
    # Create summary table
    table = Table(title=f"Scan Results Summary ({len(plugins)} plugins found)")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="magenta")
    
    # Basic stats
    table.add_row("Total Plugins", str(len(plugins)))
    table.add_row("Scan Duration", f"{duration:.1f}s")
    table.add_row("Scan Mode", "Async" if async_mode else "Sync")
    table.add_row("Avg Speed", f"{len(plugins)/duration:.1f} plugins/sec")
    
    table.add_row("", "")  # Separator
    
    # Type breakdown
    for plugin_type, count in sorted(type_counts.items()):
        table.add_row(f"{plugin_type.upper()} Plugins", str(count))
    
    table.add_row("", "")  # Separator
    
    # Top manufacturers
    top_manufacturers = sorted(manufacturer_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    for manufacturer, count in top_manufacturers:
        table.add_row(f"{manufacturer}", str(count))
    
    console.print(table)
    
    # Performance tip
    if not async_mode and len(plugins) > 20:
        console.print("\n[dim]💡 Tip: Use --async for faster scanning of large plugin libraries[/dim]")

def _display_plugin_info(plugin: PluginInfo, show_parameters: bool, test_loading: bool):
    """Display detailed plugin information with Rich formatting."""
    # Main info panel
    info_lines = [
        f"[bold]ID:[/bold] {plugin.id}",
        f"[bold]Name:[/bold] {plugin.name}",
        f"[bold]Type:[/bold] {plugin.plugin_type.upper()}",
        f"[bold]Manufacturer:[/bold] {plugin.manufacturer or 'Unknown'}",
        f"[bold]Path:[/bold] {plugin.path}",
        f"[bold]Parameters:[/bold] {len(plugin.parameters)}"
    ]
    
    panel = Panel(
        "\n".join(info_lines), 
        title=f"Plugin: {plugin.name}", 
        border_style="blue"
    )
    console.print(panel)
    
    # Parameters table
    if show_parameters and plugin.parameters:
        param_table = Table(title="Parameters")
        param_table.add_column("Parameter", style="cyan")
        param_table.add_column("Value", style="magenta")
        param_table.add_column("Type", style="green")
        
        for param in sorted(plugin.parameters.values(), key=lambda p: p.name):
            param_table.add_row(
                param.name,
                str(param.value),
                type(param.value).__name__
            )
        
        console.print(param_table)
    
    # Test loading
    if test_loading:
        with console.status("Testing plugin loading..."):
            try:
                # Test plugin loading
                import pedalboard
                test_plugin = pedalboard.load_plugin(plugin.path)
                success = test_plugin is not None
            except Exception as e:
                success = False
                error_msg = str(e)
        
        if success:
            console.print("[green]✓ Plugin loads successfully[/green]")
        else:
            console.print(f"[red]✗ Plugin failed to load: {error_msg}[/red]")

def _output_plugins(plugins: List[PluginInfo], format: str):
    """Output plugins in specified format."""
    if format == 'table':
        _output_table(plugins)
    elif format == 'json':
        _output_json(plugins)
    elif format == 'yaml':
        _output_yaml(plugins)
    elif format == 'csv':
        _output_csv(plugins)

def _output_table(plugins: List[PluginInfo]):
    """Display plugins in a rich table."""
    table = Table()
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Manufacturer", style="green")
    table.add_column("Params", justify="right", style="yellow")
    table.add_column("Path", style="blue", overflow="ellipsis")
    
    for plugin in plugins:
        table.add_row(
            plugin.name,
            plugin.plugin_type.upper(),
            plugin.manufacturer or "Unknown",
            str(len(plugin.parameters)),
            plugin.path
        )
    
    console.print(table)

def _display_cache_stats(stats: Dict[str, Any]):
    """Display cache statistics with Rich formatting."""
    table = Table(title="Cache Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="magenta")
    
    # Basic stats
    table.add_row("Total Plugins", str(stats.get('total_plugins', 0)))
    
    # Database size
    db_size = stats.get('database_size_bytes', 0)
    if db_size > 0:
        if db_size > 1024 * 1024:
            size_str = f"{db_size / (1024 * 1024):.1f} MB"
        elif db_size > 1024:
            size_str = f"{db_size / 1024:.1f} KB"
        else:
            size_str = f"{db_size} bytes"
        table.add_row("Cache Size", size_str)
    
    # Last updated
    last_updated = stats.get('last_updated')
    if last_updated:
        import datetime
        dt = datetime.datetime.fromtimestamp(float(last_updated))
        table.add_row("Last Updated", dt.strftime("%Y-%m-%d %H:%M:%S"))
    
    table.add_row("", "")  # Separator
    
    # By type
    by_type = stats.get('by_type', {})
    for plugin_type, count in sorted(by_type.items()):
        table.add_row(f"{plugin_type.upper()} Plugins", str(count))
    
    # Top manufacturers
    top_manufacturers = stats.get('top_manufacturers', {})
    if top_manufacturers:
        table.add_row("", "")  # Separator
        table.add_row("[bold]Top Manufacturers[/bold]", "")
        for manufacturer, count in list(top_manufacturers.items())[:5]:
            table.add_row(f"  {manufacturer}", str(count))
    
    console.print(table)

# Entry point
def main():
    """Main CLI entry point."""
    cli()

if __name__ == '__main__':
    main()
```

**Implementation Steps**:
1. Create comprehensive Click CLI structure
2. Implement Rich formatting for all output
3. Add advanced search and filtering capabilities
4. Create cache management subcommands
5. Add comprehensive help and examples

**Expected Impact**:
- **User Experience**: Professional CLI with rich formatting and comprehensive help
- **Discoverability**: Advanced search, filtering, and auto-completion
- **Functionality**: Cache management, plugin testing, similar plugin suggestions
- **Productivity**: Fast, intuitive commands with excellent feedback

## Phase 3: Performance Optimization and Testing (Days 11-15)

### 3.1 Async Performance Benchmarking

```python
# tests/performance/test_async_benchmarks.py
import pytest
import asyncio
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from pedalboard_pluginary import PedalboardScanner

class TestAsyncPerformance:
    """Comprehensive async performance testing."""
    
    @pytest.fixture
    def mock_plugins_dir(self, tmp_path):
        """Create realistic mock plugin directory."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        
        # Create mock VST3 files
        vst3_dir = plugins_dir / "vst3"
        vst3_dir.mkdir()
        for i in range(50):
            (vst3_dir / f"TestPlugin{i:02d}.vst3").touch()
        
        # Create mock AU files  
        au_dir = plugins_dir / "au"
        au_dir.mkdir()
        for i in range(30):
            (au_dir / f"TestAU{i:02d}.component").touch()
        
        return plugins_dir
    
    def create_mock_plugin(self, name: str, load_time: float = 0.01):
        """Create mock plugin with realistic load time."""
        mock_plugin = MagicMock()
        mock_plugin.name = name
        mock_plugin.manufacturer = "TestManufacturer"
        mock_plugin.parameters = {f"param_{i}": 0.5 for i in range(10)}
        
        def slow_load(*args, **kwargs):
            time.sleep(load_time)  # Simulate plugin loading time
            return mock_plugin
        
        return slow_load
    
    @pytest.mark.asyncio
    async def test_async_vs_sync_performance(self, mock_plugins_dir, benchmark):
        """Test that async scanning is significantly faster than sync."""
        plugin_count = 80  # Total mock plugins
        load_time_per_plugin = 0.01  # 10ms per plugin
        
        with patch('pedalboard.load_plugin') as mock_load:
            mock_load.side_effect = self.create_mock_plugin("TestPlugin", load_time_per_plugin)
            
            # Benchmark sync scanning
            sync_scanner = PedalboardScanner(
                async_mode=False,
                specific_paths=[str(mock_plugins_dir)]
            )
            
            def sync_scan():
                return sync_scanner.full_scan()
            
            sync_result = benchmark.pedantic(sync_scan, iterations=1, rounds=3)
            sync_time = benchmark.stats.stats.mean
            
            # Benchmark async scanning
            async_scanner = PedalboardScanner(
                async_mode=True,
                max_concurrent=10,
                specific_paths=[str(mock_plugins_dir)]
            )
            
            async def async_scan():
                return await async_scanner.full_scan_async()
            
            # Run async benchmark
            start_time = time.time()
            async_result = await async_scan()
            async_time = time.time() - start_time
            
            # Verify results are equivalent
            assert len(sync_result) == len(async_result)
            assert len(sync_result) == plugin_count
            
            # Verify performance improvement
            speedup = sync_time / async_time
            
            print(f"Sync time: {sync_time:.2f}s")
            print(f"Async time: {async_time:.2f}s") 
            print(f"Speedup: {speedup:.1f}x")
            
            # Assert significant performance improvement
            assert speedup >= 3.0, f"Expected 3x+ speedup, got {speedup:.1f}x"
            
            # Verify we're approaching theoretical maximum
            theoretical_min = (plugin_count * load_time_per_plugin) / 10  # 10 concurrent
            efficiency = theoretical_min / async_time
            assert efficiency >= 0.7, f"Low async efficiency: {efficiency:.2f}"
    
    @pytest.mark.asyncio
    async def test_concurrency_scaling(self, mock_plugins_dir):
        """Test performance scaling with different concurrency levels."""
        concurrency_levels = [1, 5, 10, 20]
        plugin_count = 60
        results = {}
        
        with patch('pedalboard.load_plugin') as mock_load:
            mock_load.side_effect = self.create_mock_plugin("TestPlugin", 0.02)
            
            for concurrency in concurrency_levels:
                scanner = PedalboardScanner(
                    async_mode=True,
                    max_concurrent=concurrency,
                    specific_paths=[str(mock_plugins_dir)]
                )
                
                start_time = time.time()
                plugins = await scanner.full_scan_async()
                scan_time = time.time() - start_time
                
                results[concurrency] = {
                    'time': scan_time,
                    'plugins': len(plugins),
                    'rate': len(plugins) / scan_time
                }
        
        # Verify performance scaling
        assert results[10]['rate'] > results[1]['rate'] * 3
        assert results[20]['rate'] > results[5]['rate'] * 2
        
        # Log results for analysis
        for concurrency, result in results.items():
            print(f"Concurrency {concurrency}: {result['rate']:.1f} plugins/sec")
    
    @pytest.mark.asyncio 
    async def test_memory_usage_async(self, mock_plugins_dir):
        """Test memory usage doesn't grow excessively with async scanning."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss
        
        # Create large dataset
        with patch('pedalboard.load_plugin') as mock_load:
            mock_load.side_effect = self.create_mock_plugin("TestPlugin", 0.001)
            
            scanner = PedalboardScanner(
                async_mode=True,
                max_concurrent=10,
                specific_paths=[str(mock_plugins_dir)]
            )
            
            # Scan plugins
            plugins = await scanner.full_scan_async()
            
            current_memory = process.memory_info().rss
            memory_growth = current_memory - baseline_memory
            
            # Memory growth should be reasonable
            memory_per_plugin = memory_growth / len(plugins)
            
            print(f"Memory growth: {memory_growth / 1024 / 1024:.1f} MB")
            print(f"Memory per plugin: {memory_per_plugin / 1024:.1f} KB")
            
            # Should use less than 1KB per plugin on average
            assert memory_per_plugin < 1024, f"Excessive memory usage: {memory_per_plugin:.0f} bytes/plugin"
    
    def test_error_handling_performance(self, mock_plugins_dir):
        """Test that error handling doesn't significantly impact performance."""
        with patch('pedalboard.load_plugin') as mock_load:
            # Mix of successful and failing plugins
            def mixed_load_plugin(path):
                if "05" in str(path) or "15" in str(path):  # Some fail
                    raise Exception("Mock plugin error")
                return self.create_mock_plugin("TestPlugin", 0.01)()
            
            mock_load.side_effect = mixed_load_plugin
            
            scanner = PedalboardScanner(
                async_mode=True,
                max_concurrent=10,
                specific_paths=[str(mock_plugins_dir)]
            )
            
            start_time = time.time()
            plugins = asyncio.run(scanner.full_scan_async())
            scan_time = time.time() - start_time
            
            # Should still maintain good performance despite errors
            rate = len(plugins) / scan_time
            assert rate > 20, f"Low error handling performance: {rate:.1f} plugins/sec"
```

### 3.2 SQLite Performance Testing

```python
# tests/performance/test_cache_performance.py
import pytest
import time
from pathlib import Path
from pedalboard_pluginary.cache.sqlite_backend import SQLiteCacheBackend
from pedalboard_pluginary.models import PluginInfo, PluginParameter

class TestCachePerformance:
    """SQLite cache performance testing."""
    
    @pytest.fixture
    def large_plugin_dataset(self):
        """Create large dataset for performance testing."""
        plugins = {}
        
        manufacturers = ["FabFilter", "Waves", "Native Instruments", "Steinberg", "Avid"]
        types = ["vst3", "au"]
        
        for i in range(1000):
            manufacturer = manufacturers[i % len(manufacturers)]
            plugin_type = types[i % len(types)]
            
            plugin = PluginInfo(
                id=f"{plugin_type}/TestPlugin{i:04d}",
                name=f"Test Plugin {i:04d}",
                path=f"/fake/path/TestPlugin{i:04d}.{plugin_type}",
                filename=f"TestPlugin{i:04d}.{plugin_type}",
                plugin_type=plugin_type,
                manufacturer=manufacturer,
                parameters={
                    f"param_{j}": PluginParameter(
                        name=f"Parameter {j}",
                        value=float(j % 100) / 100.0
                    )
                    for j in range(i % 50 + 1)  # Variable parameter count
                }
            )
            plugins[plugin.id] = plugin
        
        return plugins
    
    def test_sqlite_vs_json_write_performance(self, tmp_path, large_plugin_dataset, benchmark):
        """Compare SQLite vs JSON write performance."""
        sqlite_path = tmp_path / "test.db"
        json_path = tmp_path / "test.json"
        
        # Test SQLite write
        sqlite_backend = SQLiteCacheBackend(sqlite_path)
        
        def sqlite_write():
            sqlite_backend.save(large_plugin_dataset)
        
        sqlite_time = benchmark.pedantic(sqlite_write, iterations=1, rounds=3)
        
        # Test JSON write (for comparison)
        from pedalboard_pluginary.serialization import PluginSerializer
        
        def json_write():
            PluginSerializer.save_plugins(large_plugin_dataset, json_path)
        
        start_time = time.time()
        json_write()
        json_time = time.time() - start_time
        
        print(f"SQLite write: {sqlite_time:.3f}s")
        print(f"JSON write: {json_time:.3f}s")
        
        # SQLite should be competitive or faster
        assert sqlite_time < json_time * 2, "SQLite write significantly slower than JSON"
    
    def test_search_performance_scaling(self, tmp_path, large_plugin_dataset):
        """Test search performance with increasing dataset sizes."""
        sqlite_path = tmp_path / "search_test.db"
        backend = SQLiteCacheBackend(sqlite_path)
        
        # Test with different dataset sizes
        sizes = [100, 500, 1000]
        search_times = {}
        
        for size in sizes:
            # Create subset of data
            subset = dict(list(large_plugin_dataset.items())[:size])
            backend.clear()
            backend.save(subset)
            
            # Test search performance
            start_time = time.time()
            results = list(backend.search(query="Test", limit=50))
            search_time = time.time() - start_time
            
            search_times[size] = search_time
            
            print(f"Size {size}: {search_time:.4f}s ({len(results)} results)")
        
        # Search time should scale well (not linearly)
        scaling_factor = search_times[1000] / search_times[100]
        assert scaling_factor < 5, f"Poor search scaling: {scaling_factor:.1f}x"
    
    def test_indexed_vs_unindexed_search(self, tmp_path, large_plugin_dataset):
        """Compare performance with and without indexes."""
        sqlite_path = tmp_path / "index_test.db"
        backend = SQLiteCacheBackend(sqlite_path)
        backend.save(large_plugin_dataset)
        
        # Test with indexes
        start_time = time.time()
        results_with_index = list(backend.search(
            plugin_type="vst3",
            manufacturer="FabFilter",
            limit=100
        ))
        time_with_index = time.time() - start_time
        
        # Drop indexes to test without
        with backend._connect() as conn:
            conn.execute("DROP INDEX IF EXISTS idx_plugins_type")
            conn.execute("DROP INDEX IF EXISTS idx_plugins_manufacturer")
        
        start_time = time.time()
        results_without_index = list(backend.search(
            plugin_type="vst3", 
            manufacturer="FabFilter",
            limit=100
        ))
        time_without_index = time.time() - start_time
        
        # Results should be identical
        assert len(results_with_index) == len(results_without_index)
        
        # Indexed search should be faster
        speedup = time_without_index / time_with_index
        print(f"Index speedup: {speedup:.1f}x")
        assert speedup > 2, f"Insufficient index speedup: {speedup:.1f}x"
    
    def test_concurrent_access_performance(self, tmp_path, large_plugin_dataset):
        """Test performance with concurrent cache access."""
        import threading
        import queue
        
        sqlite_path = tmp_path / "concurrent_test.db"
        backend = SQLiteCacheBackend(sqlite_path)
        backend.save(large_plugin_dataset)
        
        results_queue = queue.Queue()
        
        def concurrent_search(thread_id):
            start_time = time.time()
            results = list(backend.search(
                query=f"Plugin {thread_id % 100:04d}",
                limit=10
            ))
            duration = time.time() - start_time
            results_queue.put((thread_id, duration, len(results)))
        
        # Run concurrent searches
        threads = []
        thread_count = 10
        
        start_time = time.time()
        for i in range(thread_count):
            thread = threading.Thread(target=concurrent_search, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Collect results
        thread_results = []
        while not results_queue.empty():
            thread_results.append(results_queue.get())
        
        avg_time = sum(r[1] for r in thread_results) / len(thread_results)
        total_results = sum(r[2] for r in thread_results)
        
        print(f"Concurrent access: {thread_count} threads, {avg_time:.4f}s avg, {total_results} total results")
        
        # Should handle concurrent access efficiently
        assert total_time < 2.0, f"Slow concurrent access: {total_time:.2f}s"
        assert len(thread_results) == thread_count, "Some threads failed"
```

## Phase 4: Advanced Features and Production Readiness (Days 16-20)

### 4.1 Smart Change Detection System

```python
# src/pedalboard_pluginary/cache/change_detection.py
import time
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from ..models import PluginInfo
from ..protocols import CacheBackend, PluginScanner
from ..exceptions import CacheError

logger = logging.getLogger(__name__)

class ChangeDetector:
    """Intelligent change detection for incremental plugin scanning."""
    
    def __init__(self, cache_backend: CacheBackend):
        self.cache = cache_backend
        self._last_scan_time: Optional[float] = None
    
    def detect_changes(
        self, 
        scanners: List[PluginScanner],
        scan_paths: Optional[List[Path]] = None
    ) -> Dict[str, List[Path]]:
        """Detect plugin file changes since last scan.
        
        Returns:
            Dictionary with 'added', 'modified', 'removed' file lists.
        """
        # Discover current plugin files
        current_files = self._discover_current_files(scanners, scan_paths)
        
        # Get cached plugin information
        cached_files = self._get_cached_file_info()
        
        changes = {
            "added": [],
            "modified": [],
            "removed": []
        }
        
        # Check for new and modified files
        for file_path, file_mtime in current_files.items():
            if file_path not in cached_files:
                changes["added"].append(file_path)
                logger.debug(f"New plugin file detected: {file_path}")
            else:
                cached_mtime = cached_files[file_path]
                if file_mtime > cached_mtime + 1:  # 1 second tolerance
                    changes["modified"].append(file_path)
                    logger.debug(f"Modified plugin file detected: {file_path}")
        
        # Check for removed files
        current_paths = set(current_files.keys())
        cached_paths = set(cached_files.keys())
        removed_paths = cached_paths - current_paths
        
        for removed_path in removed_paths:
            changes["removed"].append(removed_path)
            logger.debug(f"Removed plugin file detected: {removed_path}")
        
        return changes
    
    def get_incremental_scan_targets(
        self,
        scanners: List[PluginScanner],
        scan_paths: Optional[List[Path]] = None,
        force_rescan_older_than: Optional[float] = None
    ) -> Tuple[List[Path], Dict[str, List[Path]]]:
        """Get files that need scanning for incremental update.
        
        Args:
            scanners: Available plugin scanners.
            scan_paths: Specific paths to scan (optional).
            force_rescan_older_than: Force rescan of plugins older than this timestamp.
        
        Returns:
            Tuple of (files_to_scan, change_summary).
        """
        changes = self.detect_changes(scanners, scan_paths)
        
        files_to_scan = []
        files_to_scan.extend(changes["added"])
        files_to_scan.extend(changes["modified"])
        
        # Add old plugins for forced rescan
        if force_rescan_older_than:
            old_plugins = self._get_plugins_older_than(force_rescan_older_than)
            files_to_scan.extend(old_plugins)
            changes["force_rescanned"] = old_plugins
        
        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for file_path in files_to_scan:
            if file_path not in seen:
                seen.add(file_path)
                unique_files.append(file_path)
        
        return unique_files, changes
    
    def cleanup_removed_plugins(self, removed_files: List[Path]) -> int:
        """Remove plugins for deleted files from cache.
        
        Returns:
            Number of plugins removed from cache.
        """
        removed_count = 0
        
        for file_path in removed_files:
            # Find plugin ID(s) for this file path
            plugin_ids = self._find_plugin_ids_by_path(file_path)
            
            for plugin_id in plugin_ids:
                try:
                    self.cache.delete(plugin_id)
                    removed_count += 1
                    logger.info(f"Removed plugin from cache: {plugin_id}")
                except Exception as e:
                    logger.error(f"Failed to remove plugin {plugin_id}: {e}")
        
        return removed_count
    
    def update_scan_timestamp(self) -> None:
        """Update the last scan timestamp."""
        self._last_scan_time = time.time()
    
    def get_cache_age_stats(self) -> Dict[str, float]:
        """Get statistics about cache age and freshness."""
        try:
            stats = self.cache.get_stats()
            
            # Get file modification times
            if hasattr(self.cache, 'get_changed_plugins'):
                recent_threshold = time.time() - (24 * 60 * 60)  # 24 hours
                recent_plugins = self.cache.get_changed_plugins(recent_threshold)
                
                return {
                    "total_plugins": stats.get("total_plugins", 0),
                    "recently_updated": len(recent_plugins),
                    "cache_freshness": len(recent_plugins) / max(stats.get("total_plugins", 1), 1)
                }
            
            return {"total_plugins": stats.get("total_plugins", 0)}
            
        except Exception as e:
            logger.error(f"Failed to get cache age stats: {e}")
            return {}
    
    def _discover_current_files(
        self, 
        scanners: List[PluginScanner],
        scan_paths: Optional[List[Path]] = None
    ) -> Dict[Path, float]:
        """Discover all current plugin files with modification times."""
        current_files = {}
        
        for scanner in scanners:
            try:
                plugin_files = scanner.find_plugin_files(scan_paths)
                
                for file_path in plugin_files:
                    try:
                        stat = file_path.stat()
                        current_files[file_path] = stat.st_mtime
                    except (OSError, ValueError) as e:
                        logger.warning(f"Cannot stat file {file_path}: {e}")
                        
            except Exception as e:
                logger.error(f"Scanner {scanner.__class__.__name__} failed to find files: {e}")
        
        return current_files
    
    def _get_cached_file_info(self) -> Dict[Path, float]:
        """Get file paths and modification times from cache."""
        cached_files = {}
        
        try:
            # For SQLite backend, we can query file modification times efficiently
            if hasattr(self.cache, '_connect'):
                with self.cache._connect() as conn:
                    rows = conn.execute(
                        "SELECT path, file_mtime FROM plugins WHERE file_mtime > 0"
                    ).fetchall()
                    
                    for path_str, mtime in rows:
                        try:
                            path = Path(path_str)
                            cached_files[path] = float(mtime)
                        except (ValueError, TypeError):
                            continue
            else:
                # Fallback for other cache backends
                logger.warning("Cache backend doesn't support efficient file time queries")
        
        except Exception as e:
            logger.error(f"Failed to get cached file info: {e}")
        
        return cached_files
    
    def _find_plugin_ids_by_path(self, file_path: Path) -> List[str]:
        """Find plugin IDs associated with a file path."""
        plugin_ids = []
        
        try:
            if hasattr(self.cache, '_connect'):
                with self.cache._connect() as conn:
                    rows = conn.execute(
                        "SELECT id FROM plugins WHERE path = ?",
                        (str(file_path),)
                    ).fetchall()
                    
                    plugin_ids = [row[0] for row in rows]
        
        except Exception as e:
            logger.error(f"Failed to find plugin IDs for {file_path}: {e}")
        
        return plugin_ids
    
    def _get_plugins_older_than(self, timestamp: float) -> List[Path]:
        """Get plugin file paths older than given timestamp."""
        old_files = []
        
        try:
            if hasattr(self.cache, '_connect'):
                with self.cache._connect() as conn:
                    rows = conn.execute(
                        "SELECT path FROM plugins WHERE updated_at < ?",
                        (timestamp,)
                    ).fetchall()
                    
                    for row in rows:
                        try:
                            old_files.append(Path(row[0]))
                        except (ValueError, TypeError):
                            continue
        
        except Exception as e:
            logger.error(f"Failed to get old plugins: {e}")
        
        return old_files
```

### 4.2 Configuration Management System

```python
# src/pedalboard_pluginary/config.py
from pathlib import Path
from typing import List, Optional, Dict, Any
import os
import json
import logging
from dataclasses import dataclass, field, asdict
from ..constants import DEFAULT_MAX_CONCURRENT

logger = logging.getLogger(__name__)

@dataclass
class ScanConfig:
    """Configuration for plugin scanning."""
    async_mode: bool = True
    max_concurrent: int = DEFAULT_MAX_CONCURRENT
    timeout: float = 10.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    def validate(self) -> None:
        """Validate configuration values."""
        if self.max_concurrent < 1 or self.max_concurrent > 100:
            raise ValueError(f"max_concurrent must be 1-100, got {self.max_concurrent}")
        
        if self.timeout <= 0 or self.timeout > 300:
            raise ValueError(f"timeout must be 0-300 seconds, got {self.timeout}")

@dataclass  
class CacheConfig:
    """Configuration for caching."""
    backend: str = "sqlite"  # "sqlite" or "json"
    directory: Optional[Path] = None
    auto_migrate: bool = True
    vacuum_threshold: int = 1000  # Vacuum after this many operations
    backup_on_migrate: bool = True
    
    def __post_init__(self):
        if self.directory is None:
            self.directory = Path.home() / ".cache" / "pedalboard-pluginary"
    
    def validate(self) -> None:
        """Validate configuration values."""
        if self.backend not in ["sqlite", "json"]:
            raise ValueError(f"Unknown cache backend: {self.backend}")

@dataclass
class CLIConfig:
    """Configuration for CLI appearance and behavior."""
    output_format: str = "table"  # "table", "json", "yaml", "csv"
    enable_colors: bool = True
    enable_progress: bool = True
    default_limit: int = 50
    page_size: int = 20
    
    def validate(self) -> None:
        """Validate configuration values."""
        valid_formats = ["table", "json", "yaml", "csv"]
        if self.output_format not in valid_formats:
            raise ValueError(f"output_format must be one of {valid_formats}")

@dataclass
class PathConfig:
    """Configuration for plugin search paths."""
    scan_default_locations: bool = True
    additional_scan_paths: List[str] = field(default_factory=list)
    ignore_patterns: List[str] = field(default_factory=list)
    specific_paths: List[str] = field(default_factory=list)
    
    def get_additional_paths(self) -> List[Path]:
        """Get additional scan paths as Path objects."""
        return [Path(p).expanduser() for p in self.additional_scan_paths]
    
    def get_specific_paths(self) -> List[Path]:
        """Get specific paths as Path objects."""
        return [Path(p).expanduser() for p in self.specific_paths]

@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    def validate(self) -> None:
        """Validate configuration values."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {self.level}")

@dataclass
class PluginaryConfig:
    """Main configuration class for Pedalboard Pluginary."""
    scan: ScanConfig = field(default_factory=ScanConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    cli: CLIConfig = field(default_factory=CLIConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> 'PluginaryConfig':
        """Load configuration from file."""
        if not config_path.exists():
            logger.info(f"Config file {config_path} not found, using defaults")
            return cls()
        
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            # Create nested config objects
            config = cls()
            
            if 'scan' in data:
                config.scan = ScanConfig(**data['scan'])
            
            if 'cache' in data:
                cache_data = data['cache'].copy()
                if 'directory' in cache_data and cache_data['directory']:
                    cache_data['directory'] = Path(cache_data['directory']).expanduser()
                config.cache = CacheConfig(**cache_data)
            
            if 'cli' in data:
                config.cli = CLIConfig(**data['cli'])
            
            if 'paths' in data:
                config.paths = PathConfig(**data['paths'])
            
            if 'logging' in data:
                config.logging = LoggingConfig(**data['logging'])
            
            config.validate()
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            logger.info("Using default configuration")
            return cls()
    
    @classmethod
    def load_from_env(cls) -> 'PluginaryConfig':
        """Load configuration from environment variables."""
        config = cls()
        
        # Scan configuration
        if os.getenv('PLUGINARY_ASYNC_MODE'):
            config.scan.async_mode = os.getenv('PLUGINARY_ASYNC_MODE').lower() == 'true'
        
        if os.getenv('PLUGINARY_MAX_CONCURRENT'):
            config.scan.max_concurrent = int(os.getenv('PLUGINARY_MAX_CONCURRENT'))
        
        if os.getenv('PLUGINARY_TIMEOUT'):
            config.scan.timeout = float(os.getenv('PLUGINARY_TIMEOUT'))
        
        # Cache configuration
        if os.getenv('PLUGINARY_CACHE_BACKEND'):
            config.cache.backend = os.getenv('PLUGINARY_CACHE_BACKEND')
        
        if os.getenv('PLUGINARY_CACHE_DIR'):
            config.cache.directory = Path(os.getenv('PLUGINARY_CACHE_DIR')).expanduser()
        
        # CLI configuration
        if os.getenv('PLUGINARY_OUTPUT_FORMAT'):
            config.cli.output_format = os.getenv('PLUGINARY_OUTPUT_FORMAT')
        
        if os.getenv('PLUGINARY_ENABLE_COLORS'):
            config.cli.enable_colors = os.getenv('PLUGINARY_ENABLE_COLORS').lower() == 'true'
        
        # Path configuration
        if os.getenv('PLUGINARY_ADDITIONAL_PATHS'):
            additional_paths = os.getenv('PLUGINARY_ADDITIONAL_PATHS').split(os.pathsep)
            config.paths.additional_scan_paths = [p for p in additional_paths if p.strip()]
        
        if os.getenv('PLUGINARY_IGNORE_PATTERNS'):
            patterns = os.getenv('PLUGINARY_IGNORE_PATTERNS').split(',')
            config.paths.ignore_patterns = [p.strip() for p in patterns if p.strip()]
        
        # Logging configuration
        if os.getenv('PLUGINARY_LOG_LEVEL'):
            config.logging.level = os.getenv('PLUGINARY_LOG_LEVEL').upper()
        
        if os.getenv('PLUGINARY_LOG_FILE'):
            config.logging.file_path = os.getenv('PLUGINARY_LOG_FILE')
        
        config.validate()
        return config
    
    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to file."""
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict for JSON serialization
        data = asdict(self)
        
        # Convert Path objects to strings
        if data['cache']['directory']:
            data['cache']['directory'] = str(data['cache']['directory'])
        
        try:
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Configuration saved to {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save config to {config_path}: {e}")
            raise
    
    def validate(self) -> None:
        """Validate all configuration sections."""
        self.scan.validate()
        self.cache.validate()
        self.cli.validate()
        self.logging.validate()
    
    def get_cache_directory(self) -> Path:
        """Get the resolved cache directory path."""
        if self.cache.directory:
            return self.cache.directory.expanduser().resolve()
        return Path.home() / ".cache" / "pedalboard-pluginary"
    
    def merge_with_defaults(self, overrides: Dict[str, Any]) -> 'PluginaryConfig':
        """Create new config with override values."""
        config_dict = asdict(self)
        
        def deep_update(base: dict, updates: dict) -> dict:
            for key, value in updates.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = deep_update(base[key], value)
                else:
                    base[key] = value
            return base
        
        updated_dict = deep_update(config_dict, overrides)
        
        # Convert back to config object
        new_config = PluginaryConfig()
        new_config.scan = ScanConfig(**updated_dict.get('scan', {}))
        new_config.cache = CacheConfig(**updated_dict.get('cache', {}))
        new_config.cli = CLIConfig(**updated_dict.get('cli', {}))
        new_config.paths = PathConfig(**updated_dict.get('paths', {}))
        new_config.logging = LoggingConfig(**updated_dict.get('logging', {}))
        
        new_config.validate()
        return new_config

class ConfigManager:
    """Manages configuration loading and saving."""
    
    DEFAULT_CONFIG_PATHS = [
        Path.home() / ".config" / "pedalboard-pluginary" / "config.json",
        Path.home() / ".pedalboard-pluginary.json",
        Path.cwd() / ".pedalboard-pluginary.json"
    ]
    
    @classmethod
    def load_config(
        self, 
        config_path: Optional[Path] = None,
        use_env: bool = True
    ) -> PluginaryConfig:
        """Load configuration with fallback chain."""
        
        # Start with environment variables if requested
        if use_env:
            config = PluginaryConfig.load_from_env()
        else:
            config = PluginaryConfig()
        
        # Try to load from file
        if config_path:
            # Specific config file provided
            if config_path.exists():
                file_config = PluginaryConfig.load_from_file(config_path)
                return file_config
            else:
                logger.warning(f"Specified config file {config_path} not found")
        else:
            # Try default locations
            for default_path in self.DEFAULT_CONFIG_PATHS:
                if default_path.exists():
                    logger.info(f"Loading config from {default_path}")
                    file_config = PluginaryConfig.load_from_file(default_path)
                    return file_config
        
        logger.info("Using default configuration")
        return config
    
    @classmethod
    def create_default_config(cls, config_path: Path) -> None:
        """Create a default configuration file."""
        config = PluginaryConfig()
        config.save_to_file(config_path)
        logger.info(f"Created default configuration at {config_path}")
```

## Implementation Timeline and Success Metrics

### Week 1 (Days 1-5): SQLite Foundation
**Goals:**
- SQLite cache backend fully functional
- JSON to SQLite migration working
- Performance benchmarks show 10x search improvement

**Success Criteria:**
- ✅ SQLite backend handles 1000+ plugins efficiently  
- ✅ Search performance O(log n) vs O(n) JSON
- ✅ Full-text search working with FTS
- ✅ Automatic migration from JSON preserves all data

### Week 2 (Days 6-10): Modern CLI Experience  
**Goals:**
- Click CLI fully replaces Fire
- Rich formatting and comprehensive help
- Advanced search and filtering working

**Success Criteria:**
- ✅ Professional CLI with comprehensive help system
- ✅ Rich table output with colors and formatting
- ✅ Advanced filtering (type, manufacturer, parameters)
- ✅ Cache management commands functional

### Week 3 (Days 11-15): Performance and Testing
**Goals:**
- Async performance benchmarked and optimized
- Comprehensive test suite for async functionality
- Performance regression testing in place

**Success Criteria:**
- ✅ Async scanning 5x+ faster than sync
- ✅ Memory usage constant with plugin count
- ✅ 90%+ test coverage for core functionality
- ✅ Performance benchmarks prevent regressions

### Week 4 (Days 16-20): Production Readiness
**Goals:**
- Smart change detection working
- Configuration management system
- Production monitoring and error recovery

**Success Criteria:**
- ✅ Incremental updates 95% faster than full scans
- ✅ Configuration system with file and env support
- ✅ Error recovery and health monitoring working
- ✅ Ready for deployment in production environments

## Conclusion

This implementation plan transforms Pedalboard Pluginary from a basic scanning tool into a **production-ready, high-performance plugin management system**. The combination of **SQLite scalability**, **async performance**, and **modern CLI experience** creates a professional-grade tool capable of handling enterprise-scale plugin libraries.

**Key Architectural Advantages:**
- **10x search performance** with SQLite + FTS
- **5-10x scanning performance** with async/await
- **Unlimited scalability** with lazy loading and indexing
- **Professional UX** with Click + Rich formatting
- **Production reliability** with comprehensive error handling

The async foundation is already in place. Adding SQLite caching and Click CLI will complete the transformation into a world-class audio plugin management tool.