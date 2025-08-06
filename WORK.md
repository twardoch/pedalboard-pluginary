# Work Progress - 2025-08-06

## All Tasks Completed ✓

### Issue 201: JSON Output Format ✓
- Changed JSON output from list to dict with IDs as keys
- Modified the json command in CLI to output the desired format
- Tested and confirmed working

### Issue 202: Fix Manufacturer Extraction ✓
- Changed 'manufacturer' to 'manufacturer_name' in scan_single.py
- Now aligns with pedalboard's actual API (since v0.9.4)
- Will extract vendor information on next plugin rescan

### AU Plugin Scanning Fix ✓
- Fixed regex pattern in scanner_isolated.py for AU plugin discovery
- Changed from expecting numeric ID to file:// URL format
- AU plugins will now be properly discovered on macOS

### Documentation & Cleanup ✓
- Updated CHANGELOG.md with all three fixes
- Removed completed items from TODO.md
- Cleaned up issues/201.txt and issues/202.txt references