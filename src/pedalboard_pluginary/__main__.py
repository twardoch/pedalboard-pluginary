#!/usr/bin/env python3
# this_file: src/pedalboard_pluginary/__main__.py
from __future__ import annotations

import logging

import click
from rich.console import Console
from rich.table import Table

from .core import PedalboardPluginary


@click.group()
@click.option("--verbose", is_flag=True, help="Enable verbose logging.")
def cli(verbose: bool):
    """A CLI for scanning and managing audio plugins."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
    if verbose:
        Console().print("[bold yellow]Verbose mode enabled[/bold yellow]")


@cli.command()
@click.option("--rescan", is_flag=True, help="Clear the cache and scan all plugins.")
@click.option(
    "--extra-folders",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    multiple=True,
    help="Additional folders to scan for plugins.",
)
@click.option(
    "--workers",
    type=int,
    default=None,
    help="Number of parallel workers to use.",
)
@click.option(
    "--timeout",
    type=int,
    default=30,
    help="Timeout in seconds for scanning a single plugin.",
)
def scan(rescan: bool, extra_folders: tuple[str], workers: int | None, timeout: int):
    """Scan for audio plugins."""
    console = Console()
    console.print("[bold cyan]Initializing plugin scanner...[/bold cyan]")
    pluginary = PedalboardPluginary(
        max_workers=workers,
        timeout=timeout,
        verbose=click.get_current_context().find_root().params["verbose"],
    )
    pluginary.scan(rescan=rescan, extra_folders=list(extra_folders))


@cli.command("list")
@click.option("--name", help="Filter by plugin name (case-insensitive).")
@click.option("--vendor", help="Filter by vendor/manufacturer (case-insensitive).")
@click.option("--type", "plugin_type", help="Filter by plugin type (vst3, aufx).")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format (default: table).",
)
def list_plugins(
    name: str | None, vendor: str | None, plugin_type: str | None, output_format: str
):
    """List scanned plugins."""
    console = Console()
    pluginary = PedalboardPluginary()
    filters = {
        "name": name,
        "manufacturer": vendor,
        "type": plugin_type,
    }
    # Remove None values so we don't pass them to the search function
    active_filters = {k: v for k, v in filters.items() if v is not None}

    plugins = pluginary.list_plugins(**active_filters)

    if not plugins:
        if output_format == "table":
            console.print("[yellow]No plugins found matching the criteria.[/yellow]")
        elif output_format == "json":
            import json

            print(json.dumps([], indent=2))
        elif output_format == "yaml":
            print("[]")
        return

    if output_format == "json":
        import json

        print(json.dumps(plugins, indent=2))
    elif output_format == "yaml":
        try:
            import yaml

            print(yaml.dump(plugins, default_flow_style=False, sort_keys=False))
        except ImportError:
            console.print(
                "[red]YAML output requires PyYAML. Install with: pip install pyyaml[/red]"
            )
            return
    else:  # table format
        table = Table(title="Available Plugins")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Vendor", style="green")
        table.add_column("Path", style="dim")

        for plugin in plugins:
            table.add_row(
                plugin.get("name"),
                plugin.get("type"),
                plugin.get("manufacturer", "N/A"),
                plugin.get("path"),
            )

        console.print(table)


@cli.command()
def info():
    """Display scanner statistics and cache information."""
    from .data import get_cache_path

    console = Console()
    pluginary = PedalboardPluginary()

    # Get cache statistics
    plugins = pluginary.list_plugins()
    plugin_count = len(plugins)

    # Count by type
    type_counts = {}
    vendor_counts = {}
    for plugin in plugins:
        plugin_type = plugin.get("type", "unknown")
        type_counts[plugin_type] = type_counts.get(plugin_type, 0) + 1

        vendor = plugin.get("manufacturer", "Unknown")
        if vendor:
            vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1

    # Display statistics
    console.print("\n[bold cyan]Plugin Scanner Statistics[/bold cyan]")
    console.print(f"Total plugins cached: [green]{plugin_count}[/green]")

    if type_counts:
        console.print("\n[bold]Plugins by type:[/bold]")
        for ptype, count in sorted(type_counts.items()):
            console.print(f"  {ptype}: {count}")

    if vendor_counts:
        console.print(f"\n[bold]Top vendors:[/bold]")
        for vendor, count in sorted(
            vendor_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            console.print(f"  {vendor}: {count}")

    # Cache information
    cache_path = get_cache_path("plugins.db")
    journal_path = get_cache_path("scan_journal.db")

    console.print("\n[bold]Cache locations:[/bold]")
    console.print(f"  Main cache: {cache_path}")
    if cache_path.exists():
        size_mb = cache_path.stat().st_size / (1024 * 1024)
        console.print(f"  Cache size: {size_mb:.2f} MB")

    if journal_path.exists():
        console.print(f"  [yellow]Active journal found: {journal_path}[/yellow]")
        console.print(
            "  [yellow]A previous scan may have been interrupted. Run 'scan' to resume.[/yellow]"
        )


@cli.command()
def clear():
    """Clear the plugin cache."""
    console = Console()

    if click.confirm("Are you sure you want to clear the plugin cache?"):
        pluginary = PedalboardPluginary()
        pluginary.cache.clear()
        console.print("[green]Plugin cache cleared successfully.[/green]")
    else:
        console.print("[yellow]Cache clear cancelled.[/yellow]")


@cli.command()
@click.option("--output", "-o", type=click.Path(), help="Output file (default: stdout)")
@click.option("--pretty", is_flag=True, help="Pretty-print the output")
def json(output: str | None, pretty: bool):
    """Export all plugins as JSON."""
    import json as json_module

    pluginary = PedalboardPluginary()
    plugins = pluginary.list_plugins()

    # Convert list to dict with IDs as keys
    plugins_dict = {
        plugin["id"]: {k: v for k, v in plugin.items() if k != "id"}
        for plugin in plugins
    }

    json_str = json_module.dumps(plugins_dict, indent=2 if pretty else None)

    if output:
        with open(output, "w") as f:
            f.write(json_str)
        Console().print(
            f"[green]Exported {len(plugins_dict)} plugins to {output}[/green]"
        )
    else:
        print(json_str)


@cli.command()
@click.option("--output", "-o", type=click.Path(), help="Output file (default: stdout)")
def yaml(output: str | None):
    """Export all plugins as YAML."""
    console = Console()

    try:
        import yaml as yaml_module
    except ImportError:
        console.print(
            "[red]YAML export requires PyYAML. Install with: pip install pyyaml[/red]"
        )
        return

    pluginary = PedalboardPluginary()
    plugins = pluginary.list_plugins()

    yaml_str = yaml_module.dump(plugins, default_flow_style=False, sort_keys=False)

    if output:
        with open(output, "w") as f:
            f.write(yaml_str)
        console.print(f"[green]Exported {len(plugins)} plugins to {output}[/green]")
    else:
        print(yaml_str)


if __name__ == "__main__":
    cli()
