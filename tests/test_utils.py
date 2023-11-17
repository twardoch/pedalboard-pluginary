import pytest
from pedalboard_pluginary.utils import ensure_folder
from pathlib import Path

def test_ensure_folder(tmp_path):
    test_folder = tmp_path / "test_folder"
    ensure_folder(test_folder)
    assert test_folder.exists()
