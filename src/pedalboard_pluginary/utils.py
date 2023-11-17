from pathlib import Path

def ensure_folder(path):
    """ Ensure that a folder exists. """
    path.parent.mkdir(parents=True, exist_ok=True)

