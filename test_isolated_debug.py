#!/usr/bin/env python3
"""Debug the isolated scanner."""

import sys
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

from src.pedalboard_pluginary.scanner_isolated import IsolatedPedalboardScanner

def test():
    print("Testing isolated scanner with debug output...")
    scanner = IsolatedPedalboardScanner(max_workers=2, timeout=10)
    
    # Try to find some plugins
    vst3_plugins = scanner._find_vst3_plugins()
    print(f"Found {len(vst3_plugins)} VST3 plugins")
    if vst3_plugins:
        print(f"First plugin: {vst3_plugins[0]}")
    
    # Try scanning just one plugin
    if vst3_plugins:
        plugin_path = str(vst3_plugins[0])
        print(f"\nTrying to get plugin names for: {plugin_path}")
        
        # Test getting plugin names
        import subprocess
        import pedalboard
        
        try:
            names = pedalboard.VST3Plugin.get_plugin_names_for_file(plugin_path)
            print(f"Plugin names: {names}")
            
            if names:
                # Test subprocess call
                from src.pedalboard_pluginary.scanner_isolated import scan_plugin_isolated
                print(f"\nTesting subprocess scan for: {names[0]}")
                result = scan_plugin_isolated(plugin_path, names[0], "vst3", timeout=10)
                print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test()