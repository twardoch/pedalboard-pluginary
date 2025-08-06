#!/usr/bin/env python3
# this_file: src/pedalboard_pluginary/scan_single.py

"""
Standalone single-plugin scanner with journaling.
This tool loads ONE plugin, writes the result to a journal, and exits.
It is designed to be called by the main scanner process.
"""
from __future__ import annotations

import argparse
import json
import sys
import os
import warnings
import io
from pathlib import Path

# Suppress all warnings and output
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'

# Add the parent directory to the path to allow imports from the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pedalboard_pluginary.scanner_isolated import ScanJournal

def scan_single_plugin(
    plugin_path: str,
    plugin_name: str,
    plugin_type: str,
    journal_path: str,
):
    """Scan a single plugin and write the result to the journal."""
    journal = ScanJournal(Path(journal_path))
    plugin_id = plugin_path

    # Mark as scanning
    journal.update_status(plugin_id, "scanning")

    result = {
        "path": plugin_path,
        "name": plugin_name,
        "type": plugin_type,
    }

    # Save original stdout and stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    # Create string buffer to capture all output
    captured_output = io.StringIO()

    try:
        # Redirect both stdout and stderr to capture all output
        sys.stdout = captured_output
        sys.stderr = captured_output

        import pedalboard

        # Load the plugin
        plugin = pedalboard.load_plugin(plugin_path, plugin_name=plugin_name)

        # Extract parameters
        params = {}
        if hasattr(plugin, 'parameters'):
            for key in plugin.parameters.keys():
                try:
                    value = getattr(plugin, key)
                    if isinstance(value, (bool, int, float, str)):
                        params[key] = value
                    else:
                        params[key] = str(value)
                except Exception:
                    params[key] = None

        # Extract manufacturer
        manufacturer = None
        if hasattr(plugin, 'manufacturer'):
            try:
                manufacturer = str(plugin.manufacturer)
            except Exception:
                pass

        # Extract other metadata
        metadata = {}
        for attr in ['version', 'category', 'is_instrument']:
            if hasattr(plugin, attr):
                try:
                    metadata[attr] = str(getattr(plugin, attr))
                except Exception:
                    pass

        result.update({
            "params": params,
            "manufacturer": manufacturer,
            "metadata": metadata,
        })

        journal.update_status(plugin_id, "success", result)

    except Exception as e:
        # We can't know for sure if it's a timeout here, the parent process will handle that.
        # We'll mark it as a generic failure.
        journal.update_status(plugin_id, "failed", {"error": str(e)})

    finally:
        # Restore original stdout and stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        captured_output.close()
        journal.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Scan a single plugin")
    parser.add_argument("--plugin-path", required=True, help="Path to the plugin")
    parser.add_argument("--plugin-name", required=True, help="Name of the plugin")
    parser.add_argument("--plugin-type", required=True, help="Type of the plugin")
    parser.add_argument("--journal-path", required=True, help="Path to the journal database")
    
    args = parser.parse_args()
    
    scan_single_plugin(
        plugin_path=args.plugin_path,
        plugin_name=args.plugin_name,
        plugin_type=args.plugin_type,
        journal_path=args.journal_path
    )


if __name__ == "__main__":
    main()
