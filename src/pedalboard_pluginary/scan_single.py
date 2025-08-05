#!/usr/bin/env python3
# this_file: src/pedalboard_pluginary/scan_single.py

"""
Standalone single-plugin scanner.
This tool loads ONE plugin and outputs its data as JSON.
It may crash if the plugin crashes - that's expected.
"""

import json
import sys
import os
import warnings
import io

# Suppress all warnings and output
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'


def scan_single_plugin(plugin_path: str, plugin_name: str, plugin_type: str):
    """Scan a single plugin and return JSON data."""
    result = {
        "success": False,
        "path": plugin_path,
        "name": plugin_name,
        "type": plugin_type,
        "error": None,
        "params": {},
        "manufacturer": None
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
        
        # Load the plugin (all its output will be captured)
        plugin = pedalboard.load_plugin(plugin_path, plugin_name=plugin_name)
        
        # Extract parameters
        params = {}
        if hasattr(plugin, 'parameters'):
            for key in plugin.parameters.keys():
                try:
                    value = getattr(plugin, key)
                    # Convert to JSON-serializable format
                    if isinstance(value, (bool, int, float, str)):
                        params[key] = value
                    else:
                        params[key] = str(value)
                except:
                    params[key] = None
        
        # Extract manufacturer
        manufacturer = None
        if hasattr(plugin, 'manufacturer'):
            try:
                manufacturer = str(plugin.manufacturer)
            except:
                pass
        
        # Extract other metadata
        metadata = {}
        for attr in ['version', 'category', 'is_instrument']:
            if hasattr(plugin, attr):
                try:
                    metadata[attr] = str(getattr(plugin, attr))
                except:
                    pass
        
        result.update({
            "success": True,
            "params": params,
            "manufacturer": manufacturer,
            "metadata": metadata,
            "error": None
        })
        
    except Exception as e:
        result["error"] = str(e)
    
    finally:
        # Restore original stdout and stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        
        # Close the captured output buffer
        captured_output.close()
    
    # Output ONLY the JSON result
    print(json.dumps(result))


def main():
    """Main entry point."""
    if len(sys.argv) != 4:
        error_result = {
            "success": False,
            "error": "Usage: scan_single.py <plugin_path> <plugin_name> <plugin_type>"
        }
        print(json.dumps(error_result))
        sys.exit(1)
    
    plugin_path = sys.argv[1]
    plugin_name = sys.argv[2]
    plugin_type = sys.argv[3]
    
    scan_single_plugin(plugin_path, plugin_name, plugin_type)


if __name__ == "__main__":
    main()