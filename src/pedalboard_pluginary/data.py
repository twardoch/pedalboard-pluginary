import json
import os
import shutil
from pathlib import Path
from pkg_resources import resource_filename
from .utils import *

APP_NAME = "com.twardoch.pedalboard-pluginary"

def get_cache_path(cache_name):
    """ Get the path to a cache file. """
    if os.name == "nt":
        cache_folder = Path(os.getenv("APPDATA")) / APP_NAME
    else:
        cache_folder = Path.home() / "Library" / "Application Support" / APP_NAME
    return cache_folder / f"{cache_name}.json"

def load_json_file(file_path):
    """ Load JSON data from a file. """
    if file_path.exists():
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}

def save_json_file(data, file_path):
    """ Save JSON data to a file. """
    ensure_folder(file_path)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def load_ignores(ignores_path):
    """ Load ignores data from the file. """
    return set(load_json_file(ignores_path))

def save_ignores(ignores, ignores_path):
    """ Save ignores data to the file. """
    save_json_file(sorted(list(ignores)), ignores_path)

def copy_default_ignores(destination_path):
    """ Copy the default ignores file to the destination if it does not exist. """
    default_ignores_path = resource_filename(__name__, 'resources/default_ignores.json')
    if not destination_path.exists():
        ensure_folder(destination_path)
        shutil.copy(default_ignores_path, destination_path)
