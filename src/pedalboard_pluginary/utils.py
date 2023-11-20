from pathlib import Path

def ensure_folder(path):
    """ Ensure that a folder exists. """
    path.parent.mkdir(parents=True, exist_ok=True)

def from_pb_param(data):
    drep = str(data)
    try:
        return float(drep)
    except ValueError:
        pass
    if drep.lower() in ["true", "false"]:
        return drep.lower() == "true"
    return drep
