from pathlib import Path
from typing import Any, Union

def ensure_folder(path: Path) -> None:
    """ Ensure that a folder exists. """
    path.parent.mkdir(parents=True, exist_ok=True)

def from_pb_param(data: Any) -> Union[float, bool, str]:
    """
    Converts a pedalboard parameter value to a Python native type.
    Pedalboard parameter values can be string representations of floats, booleans, or just strings.
    """
    drep = str(data)
    try:
        return float(drep)
    except ValueError:
        pass
    if drep.lower() == "true":
        return True
    if drep.lower() == "false":
        return False
    return drep
