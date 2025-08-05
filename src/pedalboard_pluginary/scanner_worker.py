#!/usr/bin/env python3
# this_file: src/pedalboard_pluginary/scanner_worker.py

"""Worker process for scanning individual plugins in isolation."""

import json
import sys
import traceback
from pathlib import Path

import pedalboard

from .utils import from_pb_param


def scan_single_plugin(plugin_path: str, plugin_name: str, plugin_type: str) -> dict:
    """Scan a single plugin in isolation and return its info."""
    try:
        # Load the plugin
        plugin = pedalboard.load_plugin(plugin_path, plugin_name=plugin_name)
        
        # Extract parameters
        plugin_params = {}
        for key in plugin.parameters.keys():
            try:
                plugin_params[key] = from_pb_param(plugin.__getattr__(key))
            except Exception:
                # Skip parameters that can't be extracted
                pass
        
        # Extract manufacturer/vendor info
        manufacturer = None
        if hasattr(plugin, 'manufacturer'):
            manufacturer = plugin.manufacturer
        
        # Build plugin entry
        plugin_entry = {
            "name": plugin_name,
            "path": plugin_path,
            "filename": Path(plugin_path).stem,
            "type": plugin_type,
            "params": plugin_params,
            "success": True
        }
        
        if manufacturer:
            plugin_entry["manufacturer"] = manufacturer
            
        return plugin_entry
        
    except Exception as e:
        # Return error info
        return {
            "name": plugin_name,
            "path": plugin_path,
            "type": plugin_type,
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def main():
    """Main entry point for worker process."""
    if len(sys.argv) != 4:
        print("Usage: scanner_worker.py <plugin_path> <plugin_name> <plugin_type>")
        sys.exit(1)
    
    plugin_path = sys.argv[1]
    plugin_name = sys.argv[2]
    plugin_type = sys.argv[3]
    
    result = scan_single_plugin(plugin_path, plugin_name, plugin_type)
    
    # Output result as JSON
    print(json.dumps(result))


if __name__ == "__main__":
    main()