# tests/test_cli.py
import os
import subprocess
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from pedalboard_pluginary.data import APP_NAME, PLUGINS_CACHE_FILENAME_BASE, get_cache_path

# Helper to get the cache file path for plugins
def get_plugins_cache_file():
    return get_cache_path(PLUGINS_CACHE_FILENAME_BASE)

@pytest.fixture(autouse=True)
def manage_plugin_cache():
    """Fixture to ensure plugin cache is handled before and after tests."""
    cache_file = get_plugins_cache_file()
    original_content = None

    if cache_file.exists():
        original_content = cache_file.read_text()
        cache_file.unlink() # Remove before test

    yield # Test runs here

    # Cleanup: remove cache file created by test, or restore original
    if cache_file.exists():
        cache_file.unlink()
    if original_content:
        # Ensure parent directory exists before writing back
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(original_content)


# Mocked data for PedalboardScanner.scan_all_plugins and load_json_file
# This data will be "written" by the mocked scan and "read" by list/json/yaml
MOCK_PLUGIN_DATA = {
    "vst3/MockSynth": {
        "id": "vst3/MockSynth",
        "name": "MockSynth",
        "path": "/fake/path/to/MockSynth.vst3",
        "filename": "MockSynth.vst3",
        "plugin_type": "vst3",
        "parameters": {
            "Volume": {"name": "Volume", "value": 0.75},
            "Pan": {"name": "Pan", "value": 0.0}
        },
        "manufacturer": "FakePlugins",
        "name_in_file": "MockSynth"
    },
    "aufx/MockEffect": {
        "id": "aufx/MockEffect",
        "name": "MockEffect",
        "path": "/fake/path/to/MockEffect.component",
        "filename": "MockEffect.component",
        "plugin_type": "aufx",
        "parameters": {
            "Wet/Dry": {"name": "Wet/Dry", "value": 0.5}
        },
        "manufacturer": "FakeAudio",
        "name_in_file": "MockEffect"
    }
}

# This mock will replace the actual PedalboardScanner instance or its methods
@patch('pedalboard_pluginary.scanner.PedalboardScanner.scan_all_plugins')
@patch('pedalboard_pluginary.scanner.PedalboardScanner.update_scan') # Also mock update_scan
@patch('pedalboard_pluginary.scanner.PedalboardScanner.save_plugins') # Mock save_plugins
@patch('pedalboard_pluginary.core.PedalboardPluginary.load_data') # Mock load_data in core
def run_cli_command(
    cli_args_list,
    mock_core_load_data,
    mock_scanner_save_plugins,
    mock_scanner_update_scan,
    mock_scanner_scan_all,
    expected_exit_code=0
):
    """Helper to run CLI commands and capture output."""

    # If scan or update is called, make them "create" the mock cache file
    def side_effect_scan_or_update(*args, **kwargs):
        cache_file = get_plugins_cache_file()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(MOCK_PLUGIN_DATA, f, indent=4)
        # The actual scan methods in PedalboardScanner don't return anything.
        # They modify self.plugins and then call self.save_plugins.
        # We've mocked save_plugins separately.

    mock_scanner_scan_all.side_effect = side_effect_scan_or_update
    mock_scanner_update_scan.side_effect = side_effect_scan_or_update

    # Mock load_data to set the plugins attribute on an instance if needed,
    # or simply prevent it from trying to load a real file during list commands
    # if scan hasn't run.
    # For 'list', 'json', 'yaml', the PedalboardPluginary instance will try to load.
    # We can patch load_json_file used by PedalboardPluginary.load_data

    base_command = ["pbpluginary"]
    full_command = base_command + cli_args_list

    try:
        result = subprocess.run(full_command, capture_output=True, text=True, check=False)
        if result.returncode != expected_exit_code:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        assert result.returncode == expected_exit_code
        return result
    except FileNotFoundError:
        pytest.fail("pbpluginary command not found. Ensure it's installed and in PATH for testing.")


# Test 'scan' command
# Patching at the source of where PedalboardScanner is instantiated or used by CLI
@patch('pedalboard_pluginary.__main__.PedalboardScanner')
def test_cli_scan(MockScannerConstructor):
    # Mock the instance methods that would be called
    mock_scanner_instance = MockScannerConstructor.return_value
    mock_scanner_instance.rescan.return_value = None # rescan calls full_scan which calls scan_all_plugins

    # We need rescan (which is an alias for full_scan) to effectively create the cache
    # by having its underlying scan_all_plugins call write the MOCK_PLUGIN_DATA
    def mock_rescan_writes_cache(*args, **kwargs):
        cache_file = get_plugins_cache_file()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(MOCK_PLUGIN_DATA, f, indent=4)
    mock_scanner_instance.rescan.side_effect = mock_rescan_writes_cache

    result = run_cli_command(["scan"]) # Uses the patches from run_cli_command's decorators

    # Check that the cache file was created with mock data
    cache_file = get_plugins_cache_file()
    assert cache_file.exists()
    with open(cache_file, 'r') as f:
        data_from_cache = json.load(f)
    assert data_from_cache == MOCK_PLUGIN_DATA

    # Check if scan method on the instance was called
    mock_scanner_instance.rescan.assert_called_once()


# Test 'list' command (implicitly tests JSON output)
# For list, we need to ensure that the cache exists or that PedalboardPluginary can load it.
# The manage_plugin_cache fixture helps here.
# We also need to control what PedalboardPluginary.load_data does.
@patch('pedalboard_pluginary.data.load_json_file') # Patch where load_json_file is defined
def test_cli_list(mock_load_json, capsys):
    # Setup: Ensure a cache file with MOCK_PLUGIN_DATA exists for 'list' to read
    cache_file = get_plugins_cache_file()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(MOCK_PLUGIN_DATA, f, indent=4)

    # Configure the mock for load_json_file used by PedalboardPluginary
    # It should return the MOCK_PLUGIN_DATA when the specific plugins cache path is requested
    def side_effect_load_json(path_arg):
        if path_arg == cache_file:
            # Return raw dict, PedalboardPluginary.load_data will handle reconstruction
            return MOCK_PLUGIN_DATA
        return {} # Default for other calls
    mock_load_json.side_effect = side_effect_load_json

    # Run the 'list' command
    # Using direct function call to avoid subprocess complexity with stdout/stderr and fire's display hook
    from pedalboard_pluginary.__main__ import list_json_cli

    # Fire's Display hook is tricky to test with subprocess.run, so call directly.
    # list_json_cli returns a string.
    # We need to ensure that when `pbpluginary list` is run, this function is called
    # and its output (which is JSON string) is printed.
    # For simplicity here, just test the function that `fire` would call.

    # To test the actual CLI output, we need to let pbpluginary run as subprocess
    # and capture stdout. This means not mocking PedalboardPluginary or its load_data directly here
    # but ensuring the underlying data.load_json_file behaves as expected due to the patch.

    result = subprocess.run(["pbpluginary", "list"], capture_output=True, text=True, check=True)

    # The output should be the MOCK_PLUGIN_DATA formatted as JSON
    # Fire wraps output, so it might not be exact JSON string if printed line-by-line.
    # The default 'list' command in __main__.py calls bdict().to_json() and fire prints it.
    # Let's parse the stdout.
    try:
        output_data = json.loads(result.stdout)
        assert output_data == MOCK_PLUGIN_DATA
    except json.JSONDecodeError:
        pytest.fail(f"CLI output was not valid JSON. Output:\n{result.stdout}")


# Test 'json' command (should be identical to 'list')
@patch('pedalboard_pluginary.data.load_json_file')
def test_cli_json_output(mock_load_json_for_json_cmd, capsys):
    cache_file = get_plugins_cache_file()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(MOCK_PLUGIN_DATA, f, indent=4)

    def side_effect_load_json(path_arg):
        if path_arg == cache_file:
            return MOCK_PLUGIN_DATA
        return {}
    mock_load_json_for_json_cmd.side_effect = side_effect_load_json

    result = subprocess.run(["pbpluginary", "json"], capture_output=True, text=True, check=True)
    try:
        output_data = json.loads(result.stdout)
        assert output_data == MOCK_PLUGIN_DATA
    except json.JSONDecodeError:
        pytest.fail(f"CLI output for 'json' was not valid JSON. Output:\n{result.stdout}")


# Test 'yaml' command
@patch('pedalboard_pluginary.data.load_json_file')
def test_cli_yaml_output(mock_load_json_for_yaml_cmd, capsys):
    cache_file = get_plugins_cache_file()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(MOCK_PLUGIN_DATA, f, indent=4)

    def side_effect_load_json(path_arg):
        if path_arg == cache_file:
            return MOCK_PLUGIN_DATA
        return {}
    mock_load_json_for_yaml_cmd.side_effect = side_effect_load_json

    result = subprocess.run(["pbpluginary", "yaml"], capture_output=True, text=True, check=True)
    try:
        # python-benedict's to_yaml output might have specific formatting.
        # For robustness, parse it back and compare with original data.
        output_data = yaml.safe_load(result.stdout)
        # YAML load might produce slightly different types (e.g. list for dict items sometimes)
        # A direct comparison MOCK_PLUGIN_DATA might be tricky if numbers are float vs int.
        # For now, let's assume benedict produces standard YAML that converts back cleanly.
        assert json.dumps(output_data, sort_keys=True) == json.dumps(MOCK_PLUGIN_DATA, sort_keys=True)
    except yaml.YAMLError:
        pytest.fail(f"CLI output for 'yaml' was not valid YAML. Output:\n{result.stdout}")
    except Exception as e:
        pytest.fail(f"Error comparing YAML output: {e}. Output:\n{result.stdout}")


# Test 'update' command
@patch('pedalboard_pluginary.__main__.PedalboardScanner')
def test_cli_update(MockScannerConstructorForUpdate):
    mock_scanner_instance = MockScannerConstructorForUpdate.return_value

    # Simulate that update_scan effectively writes the cache
    def mock_update_scan_writes_cache(*args, **kwargs):
        cache_file = get_plugins_cache_file()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        # Update might add to existing data or rescan if no cache.
        # For this test, assume it behaves like scan if no cache.
        with open(cache_file, 'w') as f:
            json.dump(MOCK_PLUGIN_DATA, f, indent=4) # For simplicity, same as scan
    mock_scanner_instance.update_scan.side_effect = mock_update_scan_writes_cache

    result = run_cli_command(["update"]) # Uses patches from run_cli_command

    cache_file = get_plugins_cache_file()
    assert cache_file.exists()
    with open(cache_file, 'r') as f:
        data_from_cache = json.load(f)
    assert data_from_cache == MOCK_PLUGIN_DATA # Assuming update wrote this

    mock_scanner_instance.update_scan.assert_called_once()


# TODO: Test for verbose logging options (--verbose=1, --verbose=2)
# TODO: Test for --extra-folders option with scan and update
# TODO: Test scan/update when cache already exists (for update's diff logic, though that's scanner internal)
# TODO: Test error conditions (e.g., unparseable cache, permissions issues - harder to mock)

# Note: The run_cli_command helper and its patches are quite broad.
# For more targeted tests, especially for 'list', 'json', 'yaml',
# it might be better to directly call the CLI functions from __main__.py
# and mock their dependencies (like PedalboardPluginary instance) instead of using subprocess.
# However, subprocess tests the actual command-line invocation.
# The current `test_cli_list` and `test_cli_json_output`, `test_cli_yaml_output`
# have been changed to use subprocess.run directly.
