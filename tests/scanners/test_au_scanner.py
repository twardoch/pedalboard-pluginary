# tests/scanners/test_au_scanner.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from pedalboard_pluginary.scanners.au_scanner import AUScanner

# Sample auval output
AUVAL_OUTPUT_VALID = """
 Westwood AU Test
--------------------------------------------------
AUVALTOOL Discount AU
--------------------------------------------------
PLAYER version 2.0.13 (build 17)
--------------------------------------------------
VALIDATING AUDIO UNIT: 'aufx' - 'dely' - 'appl'
--------------------------------------------------
Manufacturer String: Apple
AudioUnit Name: AUDelay
Component Version: 1.7.0
Component Bundle Path: /Library/Audio/Plug-Ins/Components/AUDelay.component
Component AU Path: /Library/Audio/Plug-Ins/Components/AUDelay.component/Contents/MacOS/AUDelay

* * PASS
--------------------------------------------------
VALIDATING AUDIO UNIT: 'aufx' - 'mcmp' - 'appl'
--------------------------------------------------
Manufacturer String: Apple
AudioUnit Name: AUMultibandCompressor
Component Version: 1.7.0
Component Bundle Path: /Library/Audio/Plug-Ins/Components/AUMultibandCompressor.component
Component AU Path: /Library/Audio/Plug-Ins/Components/AUMultibandCompressor.component/Contents/MacOS/AUMultibandCompressor

* * PASS
--------------------------------------------------
VALIDATING AUDIO UNIT: 'aumf' - 'dls ' - 'appl'
--------------------------------------------------
Manufacturer String: Apple
AudioUnit Name: DLSMusicDevice
Component Version: 1.7.0
Component Bundle Path: /Library/Audio/Plug-Ins/Components/DLSMusicDevice.component
Component AU Path: /Library/Audio/Plug-Ins/Components/DLSMusicDevice.component/Contents/MacOS/DLSMusicDevice

* * PASS
--------------------------------------------------
TESTING OPEN TIMES:
COLD:
Time to open AudioUnit:      21.112 ms
WARM:
Time to open AudioUnit:      0.042  ms
This AudioUnit is a version 3 implementation.
FIRST TIME:
FATAL ERROR: Initialize: result: -50


--------------------------------------------------
AU VALIDATION SUCCEEDED.
--------------------------------------------------
"""

AUVAL_OUTPUT_GARBAGE_URL = """
 Westwood AU Test
--------------------------------------------------
VALIDATING AUDIO UNIT: 'aufx' - 'xxxx' - 'test'
--------------------------------------------------
Manufacturer String: Test Inc
AudioUnit Name: BadURLPlugin
Component Version: 1.0.0
Component Bundle Path: /path/to/plugin with spaces.component
Component AU Path: (null)

* * PASS
--------------------------------------------------
AU VALIDATION SUCCEEDED.
--------------------------------------------------
"""


@pytest.fixture
def au_scanner_instance():
    return AUScanner(ignores=set())

@pytest.fixture
def au_scanner_with_ignores_instance():
    return AUScanner(ignores={"aufx/DLSMusicDevice"}) # Key is type/stem

@patch('platform.system', return_value='Darwin') # Assume macOS for these tests
class TestAUScanner:

    @patch('subprocess.run')
    def test_list_aufx_plugins_raw_success(self, mock_subprocess_run, au_scanner_instance):
        mock_process = MagicMock()
        mock_process.stdout = AUVAL_OUTPUT_VALID
        mock_subprocess_run.return_value = mock_process

        lines = au_scanner_instance._list_aufx_plugins_raw()
        assert len(lines) > 0
        assert "AUDelay" in AUVAL_OUTPUT_VALID
        mock_subprocess_run.assert_called_once_with(
            ["auval", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )

    @patch('subprocess.run', side_effect=FileNotFoundError("auval not found"))
    def test_list_aufx_plugins_raw_auval_not_found(self, mock_subprocess_run, au_scanner_instance):
        lines = au_scanner_instance._list_aufx_plugins_raw()
        assert lines == []

    @patch('subprocess.run')
    def test_find_plugin_files_valid_output(self, mock_subprocess_run, au_scanner_instance):
        mock_process = MagicMock()
        mock_process.stdout = AUVAL_OUTPUT_VALID
        mock_subprocess_run.return_value = mock_process

        # Mock Path.resolve() and Path.exists() for paths found by auval
        with patch.object(Path, 'resolve') as mock_resolve, \
             patch.object(Path, 'exists', return_value=True) as mock_exists:

            # Make resolve return a Path object that can be further manipulated if needed
            # and also has an 'exists' method.
            def side_effect_resolve(*args, **kwargs):
                # The input to resolve is the path string from auval output
                # e.g., Path("/Library/Audio/Plug-Ins/Components/AUDelay.component")
                # We want it to return itself basically, but as a mock if needed for exists()
                p = Path(*args) # Reconstruct the original path
                # Mock the exists for this specific path if needed, though global mock_exists might cover it
                # For bundle path logic, ensure suffix is checked on original path.
                return p
            mock_resolve.side_effect = side_effect_resolve

            plugin_files = au_scanner_instance.find_plugin_files()

            assert len(plugin_files) == 3 # AUDelay, AUMultibandCompressor, DLSMusicDevice
            expected_paths = [
                Path("/Library/Audio/Plug-Ins/Components/AUDelay.component"),
                Path("/Library/Audio/Plug-Ins/Components/AUMultibandCompressor.component"),
                Path("/Library/Audio/Plug-Ins/Components/DLSMusicDevice.component"),
            ]
            for p in expected_paths:
                assert p.resolve() in plugin_files # Comparing resolved paths

    @patch('subprocess.run')
    def test_find_plugin_files_with_ignores(self, mock_subprocess_run, au_scanner_with_ignores_instance):
        mock_process = MagicMock()
        mock_process.stdout = AUVAL_OUTPUT_VALID
        mock_subprocess_run.return_value = mock_process

        with patch.object(Path, 'resolve', side_effect=lambda p: Path(p)), \
             patch.object(Path, 'exists', return_value=True):
            plugin_files = au_scanner_with_ignores_instance.find_plugin_files()

            # DLSMusicDevice should be ignored
            assert len(plugin_files) == 2
            ignored_path = Path("/Library/Audio/Plug-Ins/Components/DLSMusicDevice.component").resolve()
            assert ignored_path not in plugin_files
            delay_path = Path("/Library/Audio/Plug-Ins/Components/AUDelay.component").resolve()
            assert delay_path in plugin_files


    @patch('subprocess.run')
    def test_find_plugin_files_garbage_url(self, mock_subprocess_run, au_scanner_instance):
        mock_process = MagicMock()
        mock_process.stdout = AUVAL_OUTPUT_GARBAGE_URL # Contains (null) URL
        mock_subprocess_run.return_value = mock_process

        with patch.object(Path, 'resolve', side_effect=lambda p: Path(p) if p else None), \
             patch.object(Path, 'exists', return_value=True):
            plugin_files = au_scanner_instance.find_plugin_files()
            assert len(plugin_files) == 0 # Should skip the one with (null) URL

    @patch('platform.system', return_value='Linux') # Test non-Darwin platform
    def test_scanner_on_non_macos(self, mock_platform_system_linux, au_scanner_instance):
        assert au_scanner_instance._list_aufx_plugins_raw() == []
        assert au_scanner_instance.find_plugin_files() == []

    @patch('subprocess.run')
    def test_find_plugin_files_with_specific_paths_filter(self, mock_subprocess_run, au_scanner_instance):
        mock_process = MagicMock()
        mock_process.stdout = AUVAL_OUTPUT_VALID
        mock_subprocess_run.return_value = mock_process

        # User wants to check only AUDelay
        specific_paths_to_check = [Path("/Library/Audio/Plug-Ins/Components/AUDelay.component")]

        with patch.object(Path, 'resolve', side_effect=lambda p: Path(p)), \
             patch.object(Path, 'exists', return_value=True):
            plugin_files = au_scanner_instance.find_plugin_files(plugin_paths=specific_paths_to_check)

            assert len(plugin_files) == 1
            assert Path("/Library/Audio/Plug-Ins/Components/AUDelay.component").resolve() in plugin_files

    # Test for bundle path resolution logic
    # This requires more intricate mocking of Path objects if we don't want to rely on filesystem
    @patch('subprocess.run')
    def test_bundle_path_resolution(self, mock_subprocess_run, au_scanner_instance):
        # Simulate auval output where path is deep inside the bundle
        deep_path_auval_output = """
        VALIDATING AUDIO UNIT: 'aufx' - 'test' - 'tstc'
        --------------------------------------------------
        Manufacturer String: TestCompany
        AudioUnit Name: DeepTestPlugin
        Component Version: 1.0.0
        Component Bundle Path: /Some/Path/DeepTestPlugin.component/Contents/MacOS/DeepTestPlugin
        Component AU Path: /Some/Path/DeepTestPlugin.component/Contents/MacOS/DeepTestPlugin
        * * PASS
        --------------------------------------------------
        AU VALIDATION SUCCEEDED.
        --------------------------------------------------
        """
        mock_process = MagicMock()
        mock_process.stdout = deep_path_auval_output
        mock_subprocess_run.return_value = mock_process

        # We need to mock Path behavior for suffix and parent
        # The Path object created from the string should behave as expected.
        # No complex mocking needed if Path objects work as standard for these attributes.
        # We only need to ensure Path.resolve and Path.exists are controlled.

        with patch.object(Path, 'resolve', side_effect=lambda p: Path(p)), \
             patch.object(Path, 'exists', return_value=True):

            plugin_files = au_scanner_instance.find_plugin_files()

            assert len(plugin_files) == 1
            # The scanner should correctly identify the .component bundle path
            expected_bundle_path = Path("/Some/Path/DeepTestPlugin.component").resolve()
            assert expected_bundle_path in plugin_files

# TODO: Add tests for error conditions in auval (e.g., CalledProcessError)
# TODO: Add tests for when Path.resolve() or other Path operations raise exceptions
# (though these are less likely for valid path strings)
