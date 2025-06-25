# Pedalboard Pluginary - Production Readiness Roadmap

## Executive Summary

Based on comprehensive codebase analysis, Pedalboard Pluginary has excellent architectural foundations but requires significant performance and user experience improvements to become production-ready. The current implementation suffers from sequential scanning bottlenecks and lacks modern CLI features, but the protocol-based design makes these improvements straightforward to implement.

## Current State Assessment

### ✅ Completed Strengths
- **Type-safe architecture** with comprehensive TypedDict and protocol definitions
- **Modular scanner design** supporting VST3 and AU plugins with extensible BaseScanner
- **Robust error handling** with custom exception hierarchy and timeout protection
- **Unified serialization layer** with validation and type safety
- **Cross-platform support** with OS-specific path handling
- **Zero mypy errors** in strict mode - excellent type safety foundation

### ❌ Critical Performance Bottlenecks
- **Sequential scanning** - 1-2 plugins/second (should be 10-20 with async)
- **Memory inefficiency** - O(n) memory usage, loads entire cache
- **No concurrency** - Single-threaded design wastes modern hardware
- **Basic caching** - JSON files don't scale beyond 100s of plugins

### ❌ User Experience Gaps  
- **Outdated CLI** using Fire framework with poor error handling
- **No search/filtering** capabilities for large plugin libraries
- **Limited output formats** - missing tables, rich formatting
- **No configuration management** system

## Phase 1: Async Performance Revolution (Week 1-2)

### 1.1 Async Scanner Architecture (High Impact)

**Problem**: Sequential plugin scanning is the #1 performance bottleneck.

**Solution**: Implement fully async scanner with configurable concurrency.

```python
# src/pedalboard_pluginary/async_scanner.py
import asyncio
from typing import AsyncIterator, List, Optional
from .protocols import PluginScanner
from .models import PluginInfo

class AsyncScannerMixin:
    """Mixin to add async capabilities to scanners."""
    
    async def scan_plugin_async(self, path: Path) -> Optional[PluginInfo]:
        """Async wrapper for plugin scanning with timeout."""
        loop = asyncio.get_event_loop()
        try:
            # Use asyncio.to_thread for CPU-bound plugin loading
            return await asyncio.wait_for(
                asyncio.to_thread(self.scan_plugin, path),
                timeout=PLUGIN_LOAD_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning(f"Plugin {path} timed out during async scan")
            return None
    
    async def scan_plugins_batch(
        self, 
        paths: List[Path], 
        max_concurrent: int = 10,
        progress_reporter: Optional[ProgressReporter] = None
    ) -> AsyncIterator[PluginInfo]:
        """Scan multiple plugins concurrently with backpressure control."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scan_with_semaphore(path: Path) -> Optional[PluginInfo]:
            async with semaphore:
                return await self.scan_plugin_async(path)
        
        # Create tasks for all paths
        tasks = [scan_with_semaphore(path) for path in paths]
        
        # Process with progress tracking
        if progress_reporter:
            progress_reporter.start(len(tasks), f"Scanning {len(tasks)} plugins")
        
        completed = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1
            
            if progress_reporter:
                progress_reporter.update(1, f"Completed {completed}/{len(tasks)}")
            
            if result:
                yield result
        
        if progress_reporter:
            progress_reporter.finish("Scan completed")

class AsyncVST3Scanner(VST3Scanner, AsyncScannerMixin):
    """VST3 scanner with async capabilities."""
    pass

class AsyncAUScanner(AUScanner, AsyncScannerMixin):  
    """AU scanner with async capabilities."""
    pass
```

**Implementation Steps**:
1. Create AsyncScannerMixin with concurrent plugin loading
2. Implement AsyncVST3Scanner and AsyncAUScanner
3. Add configurable concurrency limits in constants
4. Update PedalboardScanner to support async mode
5. Benchmark performance improvements (target: 5-10x speedup)

**Expected Impact**: 
- **Performance**: 10-20 plugins/second (vs 1-2 current)
- **Resource Utilization**: Better CPU and I/O usage
- **User Experience**: Responsive progress reporting

### 1.2 SQLite Cache Backend (Scalability)

**Problem**: JSON file cache doesn't scale beyond 100s of plugins.

**Solution**: Implement SQLite backend with indexing and lazy loading.

```python
# src/pedalboard_pluginary/cache/sqlite_backend.py
import sqlite3
import json
from typing import Dict, Optional, Iterator, List
from pathlib import Path
from ..models import PluginInfo
from ..protocols import CacheBackend

class SQLiteCacheBackend(CacheBackend):
    """SQLite-based cache with indexed access and lazy loading."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema with indexes."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS plugins (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    plugin_type TEXT NOT NULL,
                    manufacturer TEXT,
                    data TEXT NOT NULL,
                    last_modified REAL NOT NULL,
                    created_at REAL NOT NULL
                );
                
                -- Indexes for fast searching
                CREATE INDEX IF NOT EXISTS idx_plugins_name ON plugins(name);
                CREATE INDEX IF NOT EXISTS idx_plugins_type ON plugins(plugin_type);
                CREATE INDEX IF NOT EXISTS idx_plugins_manufacturer ON plugins(manufacturer);
                CREATE INDEX IF NOT EXISTS idx_plugins_path ON plugins(path);
                CREATE INDEX IF NOT EXISTS idx_plugins_modified ON plugins(last_modified);
                
                -- Full-text search support
                CREATE VIRTUAL TABLE IF NOT EXISTS plugins_fts USING fts5(
                    id, name, manufacturer, content=plugins
                );
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
        limit: int = 100,
        offset: int = 0
    ) -> Iterator[PluginInfo]:
        """Search plugins with filters and pagination."""
        conditions = []
        params = []
        
        if query:
            # Use FTS for text search
            conditions.append("id IN (SELECT id FROM plugins_fts WHERE plugins_fts MATCH ?)")
            params.append(query)
        
        if plugin_type:
            conditions.append("plugin_type = ?")
            params.append(plugin_type)
        
        if manufacturer:
            conditions.append("manufacturer LIKE ?")
            params.append(f"%{manufacturer}%")
        
        where_clause = " AND ".join(conditions) if conditions else "1"
        
        sql = f"""
            SELECT data FROM plugins 
            WHERE {where_clause}
            ORDER BY name
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
        """Save plugins to database with transaction."""
        with self._connect() as conn:
            for plugin_id, plugin in plugins.items():
                data = PluginSerializer.plugin_to_dict(plugin)
                conn.execute("""
                    INSERT OR REPLACE INTO plugins 
                    (id, name, path, plugin_type, manufacturer, data, last_modified, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plugin_id,
                    plugin.name,
                    plugin.path,
                    plugin.plugin_type,
                    plugin.manufacturer,
                    json.dumps(data),
                    Path(plugin.path).stat().st_mtime,
                    time.time()
                ))
            
            # Update FTS index
            conn.execute("INSERT INTO plugins_fts(plugins_fts) VALUES('rebuild')")
    
    def update(self, plugin_id: str, plugin: PluginInfo) -> None:
        """Update single plugin efficiently."""
        self.save({plugin_id: plugin})
    
    def delete(self, plugin_id: str) -> None:
        """Delete plugin from cache."""
        with self._connect() as conn:
            conn.execute("DELETE FROM plugins WHERE id = ?", (plugin_id,))
    
    def clear(self) -> None:
        """Clear all plugins from cache."""
        with self._connect() as conn:
            conn.execute("DELETE FROM plugins")
    
    def exists(self) -> bool:
        """Check if cache exists and has plugins."""
        if not self.db_path.exists():
            return False
        
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM plugins").fetchone()[0]
            return count > 0
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM plugins").fetchone()[0]
            
            type_counts = {}
            for row in conn.execute("SELECT plugin_type, COUNT(*) FROM plugins GROUP BY plugin_type"):
                type_counts[row[0]] = row[1]
            
            return {
                "total_plugins": total,
                "by_type": type_counts
            }
    
    def _connect(self) -> sqlite3.Connection:
        """Create database connection with optimizations."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Performance vs safety balance
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        return conn
```

**Implementation Steps**:
1. Create cache package with SQLiteCacheBackend
2. Implement indexed search with full-text capabilities  
3. Add lazy loading for large datasets
4. Create migration from JSON to SQLite
5. Add cache statistics and management commands

**Expected Impact**:
- **Search Performance**: O(log n) vs O(n) current
- **Memory Usage**: Constant vs linear current
- **Scalability**: Handle 10,000+ plugins efficiently

### 1.3 Smart Cache Invalidation

**Problem**: No incremental updates - full rescans required.

**Solution**: File-based change detection with intelligent updates.

```python
# src/pedalboard_pluginary/cache/change_detection.py
import time
from pathlib import Path
from typing import Dict, List, Set
from ..models import PluginInfo

class ChangeDetector:
    """Detects changes in plugin files for incremental updates."""
    
    def __init__(self, cache_backend: CacheBackend):
        self.cache = cache_backend
        
    def detect_changes(self, scan_paths: List[Path]) -> Dict[str, List[Path]]:
        """Detect changed, added, and removed plugins."""
        current_files = self._discover_plugin_files(scan_paths)
        cached_plugins = self._get_cached_plugins()
        
        # Detect changes by comparing modification times
        changes = {
            "added": [],
            "modified": [],
            "removed": []
        }
        
        # Check for new and modified files
        for file_path in current_files:
            plugin_id = self._path_to_id(file_path)
            file_mtime = file_path.stat().st_mtime
            
            if plugin_id in cached_plugins:
                cached_mtime = cached_plugins[plugin_id].get("last_modified", 0)
                if file_mtime > cached_mtime:
                    changes["modified"].append(file_path)
            else:
                changes["added"].append(file_path)
        
        # Check for removed files
        cached_paths = {Path(p["path"]) for p in cached_plugins.values()}
        current_paths = set(current_files)
        removed_paths = cached_paths - current_paths
        changes["removed"].extend(removed_paths)
        
        return changes
    
    def incremental_scan(
        self, 
        scan_paths: List[Path], 
        scanners: List[PluginScanner],
        progress_reporter: Optional[ProgressReporter] = None
    ) -> Dict[str, PluginInfo]:
        """Perform incremental scan of only changed plugins."""
        changes = self.detect_changes(scan_paths)
        total_changes = len(changes["added"]) + len(changes["modified"])
        
        if progress_reporter:
            progress_reporter.start(total_changes, "Incremental scan")
        
        updated_plugins = {}
        
        # Scan new and modified plugins
        for file_path in changes["added"] + changes["modified"]:
            scanner = self._find_scanner_for_path(file_path, scanners)
            if scanner:
                plugin_info = scanner.scan_plugin(file_path)
                if plugin_info:
                    updated_plugins[plugin_info.id] = plugin_info
                
                if progress_reporter:
                    progress_reporter.update(1)
        
        # Remove deleted plugins from cache
        for removed_path in changes["removed"]:
            plugin_id = self._path_to_id(removed_path)
            self.cache.delete(plugin_id)
        
        # Update cache with new/modified plugins
        if updated_plugins:
            self.cache.save(updated_plugins)
        
        if progress_reporter:
            progress_reporter.finish(f"Updated {len(updated_plugins)} plugins")
        
        return updated_plugins
```

## Phase 2: Modern CLI Revolution (Week 3)

### 2.1 Migrate to Click + Rich

**Problem**: Fire framework is outdated and provides poor user experience.

**Solution**: Modern CLI with Click framework and Rich formatting.

```python
# src/pedalboard_pluginary/cli.py
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel
from typing import Optional

console = Console()

@click.group()
@click.version_option()
@click.option('--config-file', type=click.Path(), help='Configuration file path')
@click.option('--verbose', '-v', count=True, help='Increase verbosity')
def cli(config_file: Optional[str], verbose: int):
    """Pedalboard Pluginary - Audio plugin scanner and manager.
    
    A fast, reliable tool for discovering and managing audio plugins
    on your system. Supports VST3 and Audio Unit formats.
    """
    setup_logging(verbose)
    if config_file:
        load_config(config_file)

@cli.command()
@click.option('--async/--sync', default=True, help='Use async scanning for better performance')
@click.option('--concurrency', default=10, help='Max concurrent plugin scans (async mode)')
@click.option('--timeout', default=10.0, help='Plugin load timeout in seconds')
@click.option('--folders', help='Additional folders to scan (comma-separated)')
@click.option('--force', is_flag=True, help='Force full rescan (ignore cache)')
def scan(async_: bool, concurrency: int, timeout: float, folders: Optional[str], force: bool):
    """Scan system for audio plugins.
    
    Discovers VST3 and Audio Unit plugins in standard locations
    and any additional folders specified. Results are cached for
    faster subsequent operations.
    """
    extra_folders = folders.split(',') if folders else []
    
    with console.status("Initializing scanner...") as status:
        scanner = PedalboardPluginary(
            async_mode=async_,
            max_concurrent=concurrency,
            timeout=timeout
        )
        
        if force:
            status.update("Clearing cache...")
            scanner.clear_cache()
        
        status.update("Scanning plugins...")
        
        # Use Rich progress bar
        with Progress() as progress:
            task = progress.add_task("Scanning...", total=None)
            
            def progress_callback(current: int, total: int, message: str = ""):
                progress.update(task, completed=current, total=total, description=message)
            
            plugins = scanner.scan(
                extra_folders=extra_folders,
                progress_callback=progress_callback
            )
    
    # Display results summary
    _display_scan_summary(plugins)

@cli.command()
@click.option('--format', type=click.Choice(['table', 'json', 'yaml', 'csv']), 
              default='table', help='Output format')
@click.option('--filter', 'filter_text', help='Filter plugins by name or manufacturer')
@click.option('--type', 'plugin_type', type=click.Choice(['vst3', 'au']), 
              help='Filter by plugin type')
@click.option('--manufacturer', help='Filter by manufacturer')
@click.option('--limit', default=50, help='Limit number of results')
def list(format: str, filter_text: Optional[str], plugin_type: Optional[str], 
         manufacturer: Optional[str], limit: int):
    """List discovered plugins with filtering options.
    
    Display plugins in various formats with powerful filtering
    capabilities. Use --filter for text search across names
    and manufacturers.
    """
    scanner = PedalboardPluginary()
    
    # Apply filters
    plugins = scanner.search_plugins(
        query=filter_text,
        plugin_type=plugin_type,
        manufacturer=manufacturer,
        limit=limit
    )
    
    _output_plugins(plugins, format)

@cli.command()
@click.argument('plugin_id')
@click.option('--parameters/--no-parameters', default=True, help='Show plugin parameters')
@click.option('--test', is_flag=True, help='Test plugin loading')
def info(plugin_id: str, parameters: bool, test: bool):
    """Show detailed information about a specific plugin.
    
    PLUGIN_ID should be the full plugin identifier,
    e.g., 'vst3/FabFilter Pro-Q 3'
    """
    scanner = PedalboardPluginary()
    plugin = scanner.get_plugin(plugin_id)
    
    if not plugin:
        console.print(f"[red]Plugin '{plugin_id}' not found[/red]")
        raise click.Abort()
    
    _display_plugin_info(plugin, parameters, test)

@cli.command()
@click.argument('query')
@click.option('--limit', default=20, help='Limit number of results')
def search(query: str, limit: int):
    """Search plugins by name, manufacturer, or type.
    
    Performs full-text search across plugin metadata.
    Supports wildcards and boolean operators.
    """
    scanner = PedalboardPluginary()
    plugins = scanner.search_plugins(query=query, limit=limit)
    
    if not plugins:
        console.print(f"[yellow]No plugins found matching '{query}'[/yellow]")
        return
    
    _output_plugins(plugins, 'table')

@cli.group()
def cache():
    """Cache management commands."""
    pass

@cache.command()
def clear():
    """Clear the plugin cache."""
    scanner = PedalboardPluginary()
    scanner.clear_cache()
    console.print("[green]Cache cleared successfully[/green]")

@cache.command()
def stats():
    """Show cache statistics."""
    scanner = PedalboardPluginary()
    stats = scanner.get_cache_stats()
    _display_cache_stats(stats)

@cache.command()
def repair():
    """Repair corrupted cache."""
    scanner = PedalboardPluginary()
    
    with console.status("Repairing cache..."):
        repaired = scanner.repair_cache()
    
    if repaired:
        console.print("[green]Cache repaired successfully[/green]")
    else:
        console.print("[yellow]No cache corruption detected[/yellow]")

def _display_scan_summary(plugins: Dict[str, PluginInfo]) -> None:
    """Display scan results summary with Rich formatting."""
    table = Table(title="Scan Results Summary")
    table.add_column("Plugin Type", style="cyan")
    table.add_column("Count", justify="right", style="magenta")
    
    type_counts = {}
    for plugin in plugins.values():
        type_counts[plugin.plugin_type] = type_counts.get(plugin.plugin_type, 0) + 1
    
    for plugin_type, count in sorted(type_counts.items()):
        table.add_row(plugin_type.upper(), str(count))
    
    table.add_row("", "")  # Separator
    table.add_row("Total", str(len(plugins)), style="bold green")
    
    console.print(table)

def _output_plugins(plugins: List[PluginInfo], format: str) -> None:
    """Output plugins in specified format."""
    if format == 'table':
        _output_table(plugins)
    elif format == 'json':
        _output_json(plugins)
    elif format == 'yaml':
        _output_yaml(plugins)
    elif format == 'csv':
        _output_csv(plugins)

def _output_table(plugins: List[PluginInfo]) -> None:
    """Display plugins in a rich table."""
    table = Table()
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Manufacturer", style="green")
    table.add_column("Path", style="blue", overflow="ellipsis")
    
    for plugin in plugins:
        table.add_row(
            plugin.name,
            plugin.plugin_type.upper(),
            plugin.manufacturer or "Unknown",
            plugin.path
        )
    
    console.print(table)

def _display_plugin_info(plugin: PluginInfo, show_parameters: bool, test_loading: bool) -> None:
    """Display detailed plugin information."""
    # Main info panel
    info_text = f"""
[bold]Name:[/bold] {plugin.name}
[bold]Type:[/bold] {plugin.plugin_type.upper()}
[bold]Manufacturer:[/bold] {plugin.manufacturer or 'Unknown'}
[bold]Path:[/bold] {plugin.path}
[bold]Parameters:[/bold] {len(plugin.parameters)}
    """
    
    panel = Panel(info_text.strip(), title=f"Plugin: {plugin.name}", border_style="blue")
    console.print(panel)
    
    # Parameters table
    if show_parameters and plugin.parameters:
        param_table = Table(title="Parameters")
        param_table.add_column("Parameter", style="cyan")
        param_table.add_column("Value", style="magenta")
        param_table.add_column("Type", style="green")
        
        for param in plugin.parameters.values():
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
                # Test load the plugin
                scanner = PedalboardPluginary()
                success = scanner.test_plugin(plugin.id)
                
                if success:
                    console.print("[green]✓ Plugin loads successfully[/green]")
                else:
                    console.print("[red]✗ Plugin failed to load[/red]")
            except Exception as e:
                console.print(f"[red]✗ Error testing plugin: {e}[/red]")
```

**Implementation Steps**:
1. Replace Fire with Click for command structure
2. Add Rich for tables, progress bars, and formatting
3. Implement comprehensive help system
4. Add plugin search and filtering commands
5. Create cache management subcommands

**Expected Impact**:
- **User Experience**: Professional CLI with rich formatting
- **Discoverability**: Comprehensive help and examples
- **Functionality**: Search, filtering, and management features

### 2.2 Advanced Search and Filtering

**Problem**: No way to find specific plugins in large libraries.

**Solution**: Full-text search with multiple filter options.

```python
# src/pedalboard_pluginary/search.py
import re
from typing import List, Optional, Dict, Any, Callable
from .models import PluginInfo

class PluginSearchEngine:
    """Advanced search engine for plugin discovery."""
    
    def __init__(self, cache_backend: CacheBackend):
        self.cache = cache_backend
    
    def search(
        self,
        query: Optional[str] = None,
        plugin_type: Optional[str] = None,
        manufacturer: Optional[str] = None,
        has_parameters: Optional[List[str]] = None,
        parameter_count: Optional[tuple] = None,  # (min, max)
        sort_by: str = "name",
        sort_desc: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[PluginInfo]:
        """Comprehensive plugin search with multiple filters."""
        
        # Start with cache backend search for basic filters
        plugins = list(self.cache.search(
            query=query,
            plugin_type=plugin_type,
            manufacturer=manufacturer,
            limit=limit * 2,  # Get more for additional filtering
            offset=offset
        ))
        
        # Apply additional filters
        if has_parameters:
            plugins = self._filter_by_parameters(plugins, has_parameters)
        
        if parameter_count:
            min_params, max_params = parameter_count
            plugins = [p for p in plugins 
                      if min_params <= len(p.parameters) <= max_params]
        
        # Apply sorting
        plugins = self._sort_plugins(plugins, sort_by, sort_desc)
        
        # Apply final limit
        return plugins[:limit]
    
    def fuzzy_search(self, query: str, threshold: float = 0.6) -> List[PluginInfo]:
        """Fuzzy search using similarity matching."""
        import difflib
        
        all_plugins = list(self.cache.search(limit=10000))
        matches = []
        
        for plugin in all_plugins:
            # Check similarity against name and manufacturer
            name_similarity = difflib.SequenceMatcher(
                None, query.lower(), plugin.name.lower()
            ).ratio()
            
            manufacturer_similarity = 0
            if plugin.manufacturer:
                manufacturer_similarity = difflib.SequenceMatcher(
                    None, query.lower(), plugin.manufacturer.lower()
                ).ratio()
            
            max_similarity = max(name_similarity, manufacturer_similarity)
            
            if max_similarity >= threshold:
                matches.append((plugin, max_similarity))
        
        # Sort by similarity score
        matches.sort(key=lambda x: x[1], reverse=True)
        return [plugin for plugin, _ in matches]
    
    def suggest_similar(self, plugin_id: str, limit: int = 5) -> List[PluginInfo]:
        """Find plugins similar to the given plugin."""
        plugin = self.cache.get(plugin_id)
        if not plugin:
            return []
        
        # Find plugins with similar characteristics
        similar = []
        
        # Same manufacturer
        if plugin.manufacturer:
            manufacturer_plugins = list(self.cache.search(
                manufacturer=plugin.manufacturer,
                limit=50
            ))
            similar.extend([p for p in manufacturer_plugins if p.id != plugin_id])
        
        # Similar parameter count
        param_count = len(plugin.parameters)
        param_range_plugins = list(self.cache.search(limit=1000))
        param_similar = [
            p for p in param_range_plugins
            if abs(len(p.parameters) - param_count) <= 2 and p.id != plugin_id
        ]
        similar.extend(param_similar)
        
        # Remove duplicates and limit
        seen = set()
        unique_similar = []
        for p in similar:
            if p.id not in seen:
                seen.add(p.id)
                unique_similar.append(p)
                if len(unique_similar) >= limit:
                    break
        
        return unique_similar
    
    def _filter_by_parameters(
        self, 
        plugins: List[PluginInfo], 
        required_params: List[str]
    ) -> List[PluginInfo]:
        """Filter plugins that have specific parameters."""
        filtered = []
        
        for plugin in plugins:
            plugin_params = {p.name.lower() for p in plugin.parameters.values()}
            required_lower = {p.lower() for p in required_params}
            
            if required_lower.issubset(plugin_params):
                filtered.append(plugin)
        
        return filtered
    
    def _sort_plugins(
        self, 
        plugins: List[PluginInfo], 
        sort_by: str, 
        desc: bool
    ) -> List[PluginInfo]:
        """Sort plugins by specified criteria."""
        sort_functions = {
            "name": lambda p: p.name.lower(),
            "manufacturer": lambda p: (p.manufacturer or "").lower(),
            "type": lambda p: p.plugin_type,
            "parameters": lambda p: len(p.parameters),
            "path": lambda p: p.path
        }
        
        if sort_by not in sort_functions:
            sort_by = "name"
        
        return sorted(plugins, key=sort_functions[sort_by], reverse=desc)
```

## Phase 3: Production Hardening (Week 4)

### 3.1 Comprehensive Testing Strategy

**Problem**: Current test coverage is ~40% with gaps in critical areas.

**Solution**: Achieve 90%+ coverage with focus on reliability.

```python
# tests/integration/test_full_workflow.py
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

from pedalboard_pluginary import PedalboardPluginary
from pedalboard_pluginary.models import PluginInfo

class TestFullWorkflow:
    """Integration tests for complete scanning workflows."""
    
    @pytest.fixture
    def test_plugins_dir(self, tmp_path):
        """Create directory with mock plugin files."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        
        # Create mock VST3 files
        vst3_dir = plugins_dir / "vst3"
        vst3_dir.mkdir()
        (vst3_dir / "TestSynth.vst3").touch()
        (vst3_dir / "TestEffect.vst3").touch()
        
        # Create mock AU files
        au_dir = plugins_dir / "au"
        au_dir.mkdir()
        (au_dir / "TestAU.component").touch()
        
        return plugins_dir
    
    @pytest.mark.asyncio
    async def test_async_scanning_performance(self, test_plugins_dir, benchmark):
        """Test async scanning is faster than sync."""
        scanner = PedalboardPluginary(async_mode=True, max_concurrent=4)
        
        # Mock plugin loading to be fast but measurable
        with patch('pedalboard.load_plugin') as mock_load:
            mock_plugin = MagicMock()
            mock_plugin.name = "Test Plugin"
            mock_plugin.manufacturer = "Test Company"
            mock_plugin.parameters = {"gain": 0.5, "freq": 1000.0}
            mock_load.return_value = mock_plugin
            
            async def scan_async():
                return await scanner.scan_directory_async(test_plugins_dir)
            
            result = benchmark(asyncio.run, scan_async)
            assert len(result) > 0
    
    def test_cache_persistence(self, test_plugins_dir, tmp_path):
        """Test that cache persists between sessions."""
        cache_dir = tmp_path / "cache"
        scanner1 = PedalboardPluginary(cache_dir=cache_dir)
        
        with patch('pedalboard.load_plugin') as mock_load:
            mock_plugin = MagicMock()
            mock_plugin.name = "Persistent Plugin"
            mock_plugin.parameters = {}
            mock_load.return_value = mock_plugin
            
            # First scan
            plugins1 = scanner1.scan([test_plugins_dir])
            assert len(plugins1) > 0
        
        # Second scanner instance should load from cache
        scanner2 = PedalboardPluginary(cache_dir=cache_dir)
        plugins2 = scanner2.load_plugins()
        
        assert len(plugins2) == len(plugins1)
        assert list(plugins2.keys()) == list(plugins1.keys())
    
    def test_incremental_updates(self, test_plugins_dir):
        """Test incremental cache updates work correctly."""
        scanner = PedalboardPluginary()
        
        with patch('pedalboard.load_plugin') as mock_load:
            mock_plugin = MagicMock()
            mock_plugin.name = "Original Plugin"
            mock_load.return_value = mock_plugin
            
            # Initial scan
            plugins1 = scanner.scan([test_plugins_dir])
            initial_count = len(plugins1)
            
            # Add new plugin file
            new_plugin = test_plugins_dir / "vst3" / "NewPlugin.vst3"
            new_plugin.touch()
            
            # Update scan should detect new plugin
            plugins2 = scanner.update_scan([test_plugins_dir])
            assert len(plugins2) == initial_count + 1
    
    def test_error_recovery(self, test_plugins_dir):
        """Test graceful handling of plugin loading errors."""
        scanner = PedalboardPluginary()
        
        def mock_load_plugin(path):
            if "TestSynth" in str(path):
                raise Exception("Plugin corrupted")
            mock_plugin = MagicMock()
            mock_plugin.name = "Working Plugin"
            mock_plugin.parameters = {}
            return mock_plugin
        
        with patch('pedalboard.load_plugin', side_effect=mock_load_plugin):
            plugins = scanner.scan([test_plugins_dir])
            
            # Should have some plugins despite errors
            assert len(plugins) > 0
            
            # Error should be logged but not crash
            working_plugins = [p for p in plugins.values() 
                             if p.name == "Working Plugin"]
            assert len(working_plugins) > 0

# tests/performance/test_benchmarks.py
import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

class TestPerformanceBenchmarks:
    """Performance regression tests."""
    
    def test_scan_performance_regression(self, benchmark):
        """Ensure scan performance doesn't regress."""
        # Create mock plugins that take realistic time to load
        def slow_load_plugin(path):
            time.sleep(0.01)  # 10ms per plugin
            mock_plugin = MagicMock()
            mock_plugin.name = f"Plugin {Path(path).stem}"
            mock_plugin.parameters = {"param1": 0.5}
            return mock_plugin
        
        scanner = PedalboardPluginary()
        mock_paths = [Path(f"/fake/plugin{i}.vst3") for i in range(10)]
        
        with patch('pedalboard.load_plugin', side_effect=slow_load_plugin), \
             patch.object(scanner, 'find_plugin_files', return_value=mock_paths):
            
            result = benchmark(scanner.scan, [])
            assert len(result) == 10
            
            # Should complete 10 plugins in under 1 second with async
            # (much faster than 10 * 0.01 = 0.1s sequential minimum)
    
    def test_memory_usage_scaling(self):
        """Test memory usage scales properly with plugin count."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Measure baseline memory
        baseline_memory = process.memory_info().rss
        
        # Create scanner with large mock dataset
        scanner = PedalboardPluginary()
        
        # Create 1000 mock plugins
        large_dataset = {}
        for i in range(1000):
            plugin = PluginInfo(
                id=f"plugin_{i}",
                name=f"Plugin {i}",
                path=f"/fake/plugin{i}.vst3",
                filename=f"plugin{i}.vst3",
                plugin_type="vst3",
                parameters={}
            )
            large_dataset[plugin.id] = plugin
        
        scanner.plugins = large_dataset
        
        # Memory should not grow excessively
        current_memory = process.memory_info().rss
        memory_growth = current_memory - baseline_memory
        
        # Should use less than 50MB for 1000 plugins
        assert memory_growth < 50 * 1024 * 1024

# tests/reliability/test_error_scenarios.py
class TestErrorScenarios:
    """Test error handling and recovery scenarios."""
    
    def test_corrupted_cache_recovery(self, tmp_path):
        """Test recovery from corrupted cache file."""
        cache_file = tmp_path / "plugins.json"
        cache_file.write_text("invalid json content")
        
        scanner = PedalboardPluginary(cache_dir=tmp_path)
        
        # Should handle corrupted cache gracefully
        plugins = scanner.load_plugins()
        assert isinstance(plugins, dict)
        assert len(plugins) == 0
    
    def test_permission_denied_handling(self, tmp_path):
        """Test handling of permission denied errors."""
        restricted_dir = tmp_path / "restricted"
        restricted_dir.mkdir(mode=0o000)  # No permissions
        
        scanner = PedalboardPluginary()
        
        try:
            # Should not crash on permission errors
            plugins = scanner.scan([restricted_dir])
            assert isinstance(plugins, dict)
        finally:
            restricted_dir.chmod(0o755)  # Restore permissions for cleanup
    
    def test_network_drive_timeouts(self):
        """Test handling of slow network drives."""
        # Mock slow file system operations
        def slow_stat():
            time.sleep(2)  # Simulate slow network
            raise OSError("Network timeout")
        
        scanner = PedalboardPluginary(timeout=1.0)
        
        with patch.object(Path, 'stat', side_effect=slow_stat):
            # Should timeout gracefully
            plugins = scanner.scan([Path("/fake/network/path")])
            assert isinstance(plugins, dict)
```

**Implementation Steps**:
1. Create comprehensive integration test suite
2. Add performance benchmarks and regression tests
3. Test error scenarios and edge cases
4. Add cross-platform compatibility tests
5. Implement continuous integration with multiple Python versions

**Expected Impact**:
- **Reliability**: Catch regressions before deployment
- **Performance**: Prevent performance degradation
- **Confidence**: Thorough testing enables rapid development

### 3.2 Error Recovery and Resilience

**Problem**: Limited error recovery capabilities.

**Solution**: Comprehensive error handling with automatic recovery.

```python
# src/pedalboard_pluginary/resilience.py
import logging
import time
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path

class ResilienceManager:
    """Manages error recovery and system resilience."""
    
    def __init__(self, config: 'Settings'):
        self.config = config
        self.error_counts: Dict[str, int] = {}
        self.blacklisted_plugins: Set[str] = set()
        self.logger = logging.getLogger(__name__)
    
    def safe_plugin_scan(
        self, 
        scanner: PluginScanner, 
        plugin_path: Path,
        max_retries: int = 3
    ) -> Optional[PluginInfo]:
        """Safely scan a plugin with error recovery."""
        plugin_key = str(plugin_path)
        
        # Check if plugin is blacklisted
        if plugin_key in self.blacklisted_plugins:
            self.logger.debug(f"Skipping blacklisted plugin: {plugin_path}")
            return None
        
        for attempt in range(max_retries):
            try:
                return scanner.scan_plugin(plugin_path)
                
            except TimeoutError as e:
                self.logger.warning(f"Plugin {plugin_path} timed out (attempt {attempt + 1})")
                self._record_error(plugin_key, "timeout")
                
                if attempt == max_retries - 1:
                    self._maybe_blacklist_plugin(plugin_key)
                    
            except PluginLoadError as e:
                self.logger.error(f"Plugin {plugin_path} failed to load: {e}")
                self._record_error(plugin_key, "load_error")
                
                # Don't retry load errors - they're likely permanent
                self._maybe_blacklist_plugin(plugin_key)
                break
                
            except Exception as e:
                self.logger.error(f"Unexpected error scanning {plugin_path}: {e}")
                self._record_error(plugin_key, "unexpected")
                
                if attempt == max_retries - 1:
                    self._maybe_blacklist_plugin(plugin_key)
        
        return None
    
    def safe_cache_operation(
        self, 
        operation: Callable[[], Any], 
        operation_name: str,
        fallback: Optional[Callable[[], Any]] = None
    ) -> Any:
        """Safely perform cache operation with fallback."""
        try:
            return operation()
            
        except (IOError, OSError) as e:
            self.logger.error(f"Cache {operation_name} failed: {e}")
            
            if fallback:
                self.logger.info(f"Attempting {operation_name} fallback")
                try:
                    return fallback()
                except Exception as fallback_error:
                    self.logger.error(f"Fallback also failed: {fallback_error}")
            
            # Return safe default
            return {} if "load" in operation_name else None
            
        except Exception as e:
            self.logger.error(f"Unexpected error in cache {operation_name}: {e}")
            return {} if "load" in operation_name else None
    
    def repair_cache(self, cache_backend: CacheBackend) -> bool:
        """Attempt to repair corrupted cache."""
        try:
            # Test basic cache operations
            cache_backend.exists()
            test_plugins = list(cache_backend.search(limit=1))
            
            self.logger.info("Cache appears healthy")
            return False
            
        except Exception as e:
            self.logger.warning(f"Cache corruption detected: {e}")
            
            try:
                # Attempt repair by clearing and rebuilding
                self.logger.info("Attempting cache repair...")
                cache_backend.clear()
                
                # Cache will be rebuilt on next scan
                self.logger.info("Cache cleared for rebuild")
                return True
                
            except Exception as repair_error:
                self.logger.error(f"Cache repair failed: {repair_error}")
                return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status."""
        total_errors = sum(self.error_counts.values())
        
        return {
            "total_errors": total_errors,
            "blacklisted_plugins": len(self.blacklisted_plugins),
            "error_breakdown": dict(self.error_counts),
            "health_score": self._calculate_health_score()
        }
    
    def _record_error(self, plugin_key: str, error_type: str) -> None:
        """Record error for tracking."""
        error_key = f"{plugin_key}:{error_type}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
    
    def _maybe_blacklist_plugin(self, plugin_key: str) -> None:
        """Blacklist plugin if it has too many errors."""
        plugin_errors = sum(
            count for key, count in self.error_counts.items()
            if key.startswith(plugin_key)
        )
        
        if plugin_errors >= self.config.max_plugin_errors:
            self.blacklisted_plugins.add(plugin_key)
            self.logger.warning(f"Blacklisted problematic plugin: {plugin_key}")
    
    def _calculate_health_score(self) -> float:
        """Calculate system health score (0-100)."""
        total_errors = sum(self.error_counts.values())
        blacklisted_count = len(self.blacklisted_plugins)
        
        # Simple scoring algorithm
        error_penalty = min(total_errors * 2, 50)  # Max 50 point penalty
        blacklist_penalty = min(blacklisted_count * 5, 30)  # Max 30 point penalty
        
        return max(0, 100 - error_penalty - blacklist_penalty)
```

## Phase 4: Advanced Features (Week 5-6)

### 4.1 Configuration Management System

**Problem**: No user configuration system.

**Solution**: Pydantic-based settings with environment variable support.

```python
# src/pedalboard_pluginary/config.py
from pydantic import BaseSettings, validator
from typing import List, Optional
from pathlib import Path

class Settings(BaseSettings):
    """Application configuration with environment variable support."""
    
    # Performance settings
    async_mode: bool = True
    max_concurrent_scans: int = 10
    plugin_load_timeout: float = 10.0
    
    # Cache settings
    cache_backend: str = "sqlite"  # "json" or "sqlite"
    cache_directory: Optional[Path] = None
    max_cache_size_mb: int = 100
    
    # Scanning settings
    scan_default_locations: bool = True
    extra_scan_paths: List[str] = []
    ignore_patterns: List[str] = []
    
    # Error handling
    max_plugin_errors: int = 3
    enable_error_recovery: bool = True
    
    # Output settings
    default_output_format: str = "table"
    enable_colors: bool = True
    
    class Config:
        env_prefix = "PLUGINARY_"
        env_file = ".env"
        case_sensitive = False
    
    @validator('cache_directory')
    def validate_cache_directory(cls, v):
        if v is None:
            return Path.home() / ".cache" / "pedalboard-pluginary"
        return Path(v)
    
    @validator('max_concurrent_scans')
    def validate_concurrency(cls, v):
        if v < 1:
            raise ValueError("max_concurrent_scans must be at least 1")
        if v > 50:
            raise ValueError("max_concurrent_scans should not exceed 50")
        return v
```

### 4.2 Plugin Categorization System

**Problem**: No way to organize plugins by function.

**Solution**: Intelligent categorization based on names and parameters.

```python
# src/pedalboard_pluginary/categorizer.py
from enum import Enum
from typing import List, Set, Dict
import re

class PluginCategory(Enum):
    EQUALIZER = "equalizer"
    COMPRESSOR = "compressor"
    REVERB = "reverb"
    DELAY = "delay"
    MODULATION = "modulation"
    DISTORTION = "distortion"
    SYNTHESIZER = "synthesizer"
    UTILITY = "utility"
    UNKNOWN = "unknown"

class PluginCategorizer:
    """Automatically categorize plugins based on name and parameters."""
    
    CATEGORY_RULES = {
        PluginCategory.EQUALIZER: {
            "name_keywords": ["eq", "equalizer", "filter", "shelf", "bell"],
            "parameter_keywords": ["frequency", "freq", "gain", "q", "bandwidth"],
            "parameter_patterns": [r".*freq.*", r".*hz.*", r".*khz.*"]
        },
        PluginCategory.COMPRESSOR: {
            "name_keywords": ["comp", "compressor", "limiter", "gate"],
            "parameter_keywords": ["threshold", "ratio", "attack", "release", "knee"],
            "parameter_patterns": [r".*thresh.*", r".*ratio.*"]
        },
        PluginCategory.REVERB: {
            "name_keywords": ["reverb", "verb", "hall", "room", "plate", "spring"],
            "parameter_keywords": ["decay", "size", "damping", "predelay"],
            "parameter_patterns": [r".*room.*", r".*hall.*", r".*decay.*"]
        },
        PluginCategory.DELAY: {
            "name_keywords": ["delay", "echo", "ping", "pong"],
            "parameter_keywords": ["delay", "feedback", "time", "sync"],
            "parameter_patterns": [r".*delay.*", r".*time.*", r".*sync.*"]
        },
        PluginCategory.MODULATION: {
            "name_keywords": ["chorus", "flanger", "phaser", "tremolo", "vibrato", "mod"],
            "parameter_keywords": ["rate", "depth", "lfo", "speed"],
            "parameter_patterns": [r".*rate.*", r".*depth.*", r".*lfo.*"]
        },
        PluginCategory.DISTORTION: {
            "name_keywords": ["dist", "overdrive", "fuzz", "saturator", "drive"],
            "parameter_keywords": ["drive", "gain", "distortion", "saturation"],
            "parameter_patterns": [r".*drive.*", r".*dist.*", r".*sat.*"]
        },
        PluginCategory.SYNTHESIZER: {
            "name_keywords": ["synth", "osc", "generator", "bass", "lead", "pad"],
            "parameter_keywords": ["oscillator", "envelope", "filter", "cutoff"],
            "parameter_patterns": [r".*osc.*", r".*env.*", r".*adsr.*"]
        }
    }
    
    def categorize(self, plugin: PluginInfo) -> List[PluginCategory]:
        """Categorize a plugin based on its characteristics."""
        categories = []
        
        for category, rules in self.CATEGORY_RULES.items():
            if self._matches_category(plugin, rules):
                categories.append(category)
        
        return categories if categories else [PluginCategory.UNKNOWN]
    
    def _matches_category(self, plugin: PluginInfo, rules: Dict) -> bool:
        """Check if plugin matches category rules."""
        score = 0
        
        # Check name keywords
        name_lower = plugin.name.lower()
        name_matches = sum(1 for keyword in rules["name_keywords"] 
                          if keyword in name_lower)
        score += name_matches * 3  # Name matches are weighted highly
        
        # Check parameter keywords and patterns
        param_names = [p.name.lower() for p in plugin.parameters.values()]
        
        param_keyword_matches = 0
        for param_name in param_names:
            for keyword in rules["parameter_keywords"]:
                if keyword in param_name:
                    param_keyword_matches += 1
        
        param_pattern_matches = 0
        for param_name in param_names:
            for pattern in rules["parameter_patterns"]:
                if re.search(pattern, param_name):
                    param_pattern_matches += 1
        
        score += param_keyword_matches * 2
        score += param_pattern_matches * 1
        
        # Threshold for categorization
        return score >= 2
```

## Implementation Priorities

### Immediate Next Steps (Week 1)
1. **Async Scanner Implementation** - Highest impact performance improvement
2. **SQLite Cache Backend** - Essential for scalability
3. **Click CLI Migration** - Better user experience

### Quality Gates
- **Phase 1**: Async scanning 5x faster than sync, zero mypy errors
- **Phase 2**: Modern CLI with rich output, search functionality working  
- **Phase 3**: 90%+ test coverage, comprehensive error handling
- **Phase 4**: Production-ready with advanced features

### Success Metrics
- **Performance**: 10-20 plugins/second scan speed
- **Scalability**: Handle 10,000+ plugins efficiently
- **Reliability**: Graceful error handling and recovery
- **Usability**: Intuitive CLI with comprehensive help

The codebase has excellent foundations. These improvements will transform it into a production-ready, high-performance tool that can handle large plugin libraries efficiently while providing an excellent user experience.