#!/usr/bin/env python3
import os
import fire
from benedict import benedict as bdict

from .core import PedalboardPluginary
from .scanner import PedalboardScanner


def get_scanner(isolated=False, workers=4, verbose=False):
    """Factory method to get appropriate scanner instance.
    
    Args:
        isolated: Use completely isolated scanner (recommended)
        workers: Number of worker processes (default=4)
        verbose: Enable verbose output
    """
    if isolated:
        # Use completely isolated scanner (recommended)
        from .scanner_isolated import IsolatedPedalboardScanner
        return IsolatedPedalboardScanner(max_workers=workers, verbose=verbose)
    else:
        return PedalboardScanner()


def scan_plugins(extra_folders=None, workers=4, verbose=False):
    """Scan all plugins.
    
    Args:
        extra_folders: Comma-separated list of additional folders to scan
        isolated: Use completely isolated scanner (recommended, default=True)
        workers: Number of worker processes (default=4)
        verbose: Show verbose output
    """
    if verbose:
        import logging
        from rich.console import Console
        import sys
        
        # Setup comprehensive logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        console = Console()
        console.print("[bold cyan]═══ VERBOSE MODE ENABLED ═══[/bold cyan]")
        console.print(f"[yellow]Configuration:[/yellow]")
        console.print(f"  • Mode: [green]{'Parallel isolated' if workers > 1 else 'Single-threaded'}[/green]")
        console.print(f"  • Worker processes: [green]{workers}[/green]")
        console.print(f"  • Extra folders: [green]{extra_folders if extra_folders else 'None'}[/green]")
        console.print(f"  • Cache location: [blue]{os.path.expanduser('~/.pedalboard_pluginary')}[/blue]")
        console.print("[dim]────────────────────────────[/dim]\n")
        
        # Enable debug logging for all pedalboard_pluginary modules
        loggers = [
            'pedalboard_pluginary',
            'pedalboard_pluginary.scanner',
            'pedalboard_pluginary.scanner_isolated',
            'pedalboard_pluginary.scanner_worker',
            'pedalboard_pluginary.cache',
            'pedalboard_pluginary.core'
        ]
        for logger_name in loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
            
    if extra_folders:
        if isinstance(extra_folders, str):
            extra_folders = extra_folders.split(",")
        elif not isinstance(extra_folders, list):
            extra_folders = None
    
    scanner = get_scanner(workers=workers, verbose=verbose)
    
    if verbose:
        console.print(f"[cyan]Starting scan with {scanner.__class__.__name__}...[/cyan]\n")
    
    scanner.rescan(extra_folders=extra_folders)


def update_plugins(extra_folders=None, workers=4, verbose=False):
    """Update plugin cache with new plugins only.
    
    Args:
        extra_folders: Comma-separated list of additional folders to scan
        isolated: Use completely isolated scanner (recommended, default=True)
        workers: Number of worker processes (default=4)
        verbose: Show verbose output
    """
    if verbose:
        import logging
        from rich.console import Console
        import sys
        
        # Setup comprehensive logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        console = Console()
        console.print("[bold cyan]═══ VERBOSE MODE ENABLED (UPDATE) ═══[/bold cyan]")
        console.print(f"[yellow]Configuration:[/yellow]")
        console.print(f"  • Mode: [green]{'Parallel isolated' if workers > 1 else 'Single-threaded'}[/green]")
        console.print(f"  • Worker processes: [green]{workers}[/green]")
        console.print(f"  • Extra folders: [green]{extra_folders if extra_folders else 'None'}[/green]")
        console.print("[dim]────────────────────────────[/dim]\n")
        
        # Enable debug logging for all pedalboard_pluginary modules
        loggers = [
            'pedalboard_pluginary',
            'pedalboard_pluginary.scanner',
            'pedalboard_pluginary.scanner_isolated',
            'pedalboard_pluginary.scanner_worker',
            'pedalboard_pluginary.cache',
            'pedalboard_pluginary.core'
        ]
        for logger_name in loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
            
    if extra_folders:
        if isinstance(extra_folders, str):
            extra_folders = extra_folders.split(",")
        elif not isinstance(extra_folders, list):
            extra_folders = None
    
    scanner = get_scanner(workers=workers, verbose=verbose)
    
    if verbose:
        console.print(f"[cyan]Starting update with {scanner.__class__.__name__}...[/cyan]\n")
    
    scanner.update(extra_folders=extra_folders)


def list_json():
    return bdict(PedalboardPluginary().plugins).to_json()


def list_yaml():
    return bdict(PedalboardPluginary().plugins).to_yaml()


def scan_one(plugin_path):
    """Scan a single plugin for testing.
    
    Args:
        plugin_path: Path to the plugin file
    """
    from rich.console import Console
    from .scanner_isolated import scan_plugin_isolated
    import pedalboard
    
    console = Console()
    console.print(f"[cyan]Scanning single plugin: {plugin_path}[/cyan]")
    
    # Determine plugin type
    if plugin_path.endswith('.vst3'):
        plugin_type = 'vst3'
        loader = pedalboard.VST3Plugin
    elif plugin_path.endswith('.component'):
        plugin_type = 'aufx'
        loader = pedalboard.AudioUnitPlugin
    else:
        console.print(f"[red]Unknown plugin type: {plugin_path}[/red]")
        return
    
    try:
        # Get plugin names
        plugin_names = loader.get_plugin_names_for_file(plugin_path)
        console.print(f"Found {len(plugin_names)} plugin(s): {plugin_names}")
        
        for name in plugin_names:
            console.print(f"\n[yellow]Scanning: {name}[/yellow]")
            result = scan_plugin_isolated(plugin_path, name, plugin_type, timeout=30)
            
            if result.get("success"):
                console.print(f"[green]✓ Success[/green]")
                console.print(f"  Manufacturer: {result.get('manufacturer', 'Unknown')}")
                console.print(f"  Version: {result.get('metadata', {}).get('version', 'Unknown')}")
                console.print(f"  Parameters: {len(result.get('params', {}))}")
            else:
                console.print(f"[red]✗ Failed: {result.get('error')}[/red]")
                
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def info():
    """Show plugin scanner information and statistics."""
    from rich.console import Console
    from rich.table import Table
    from .data import get_cache_path, load_json_file
    
    console = Console()
    
    # Load plugin cache
    plugins_path = get_cache_path("plugins")
    if plugins_path.exists():
        plugins = load_json_file(plugins_path)
        
        # Create statistics table
        table = Table(title="Plugin Scanner Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        # Count by type
        vst3_count = sum(1 for p in plugins.values() if p.get("type") == "vst3")
        au_count = sum(1 for p in plugins.values() if p.get("type") == "aufx")
        
        # Count with manufacturer info
        with_vendor = sum(1 for p in plugins.values() if p.get("manufacturer"))
        
        table.add_row("Total Plugins", str(len(plugins)))
        table.add_row("VST3 Plugins", str(vst3_count))
        table.add_row("AU Plugins", str(au_count))
        table.add_row("With Vendor Info", str(with_vendor))
        table.add_row("Cache Location", str(plugins_path))
        
        console.print(table)
        
        # Check for failed plugins
        failed_path = get_cache_path("failed_plugins")
        if failed_path.exists():
            failed = load_json_file(failed_path)
            if failed:
                console.print(f"\n[yellow]Warning:[/yellow] {len(failed)} plugins failed to scan")
                console.print(f"See {failed_path} for details")
    else:
        console.print("[red]No plugin cache found. Run 'scan' first.[/red]")


def main(): # Renamed from cli
    fire.core.Display = lambda lines, out: print(*lines, file=out)
    fire.Fire(
        {
            "scan": scan_plugins,
            "update": update_plugins,
            "list": list_json,
            "json": list_json,
            "yaml": list_yaml,
            "info": info,
            "scan-one": scan_one,
        }
    )


if __name__ == "__main__":
    main() # Renamed from cli()
