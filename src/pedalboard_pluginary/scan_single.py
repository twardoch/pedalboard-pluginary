#!/usr/bin/env python3
# this_file: src/pedalboard_pluginary/scan_single.py

"""
Standalone single-plugin scanner with journaling.
This tool loads ONE plugin, writes the result to a journal, and exits.
It is designed to be called by the main scanner process.
"""

from __future__ import annotations

import argparse
import sys
import os
import warnings
import io
from pathlib import Path

# Suppress all warnings and output
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

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

    # Use plugin_path as the journal ID consistently
    journal_id = plugin_path

    # Mark as scanning (note: may already be marked by parent process)
    # Only update if not already scanning to avoid conflicts
    pending = journal.get_pending_plugins()
    if journal_id in pending:
        journal.update_status(journal_id, "scanning")

    # Generate the plugin data ID and filename
    plugin_filename = Path(plugin_path).name
    plugin_data_id = f"{plugin_type}/{Path(plugin_path).stem}"

    result = {
        "id": plugin_data_id,
        "path": plugin_path,
        "name": plugin_name,
        "filename": plugin_filename,
        "plugin_type": plugin_type,
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

        # Extract parameters in the expected format
        parameters = {}
        if hasattr(plugin, "parameters"):
            for key in plugin.parameters.keys():
                try:
                    value = getattr(plugin, key)
                    if isinstance(value, (bool, int, float, str)):
                        param_value = value
                    else:
                        param_value = str(value)
                    # Store as SerializedParameter format
                    parameters[key] = {"name": key, "value": param_value}
                except Exception:
                    # Skip parameters that can't be retrieved
                    pass

        # Extract manufacturer
        manufacturer = None
        if hasattr(plugin, "manufacturer_name"):
            try:
                manufacturer = str(plugin.manufacturer_name)
            except Exception:
                pass

        # Extract other metadata (store separately, not part of core model)
        metadata = {}
        for attr in ["version", "category", "is_instrument"]:
            if hasattr(plugin, attr):
                try:
                    metadata[attr] = str(getattr(plugin, attr))
                except Exception:
                    pass

        result.update(
            {
                "parameters": parameters,
                "manufacturer": manufacturer,
                # metadata is not part of the expected SerializedPlugin format
                # but we can keep it for future use if needed
            }
        )

        journal.update_status(journal_id, "success", result)

    except Exception as e:
        # We can't know for sure if it's a timeout here, the parent process will handle that.
        # We'll mark it as a generic failure.
        journal.update_status(journal_id, "failed", {"error": str(e)})

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
    parser.add_argument(
        "--journal-path", required=True, help="Path to the journal database"
    )

    args = parser.parse_args()

    scan_single_plugin(
        plugin_path=args.plugin_path,
        plugin_name=args.plugin_name,
        plugin_type=args.plugin_type,
        journal_path=args.journal_path,
    )


if __name__ == "__main__":
    main()
