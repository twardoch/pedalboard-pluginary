def ensure_folder(path):
    """Ensure that a folder exists. If path is a file, ensure its parent directory exists."""
    if path.suffix:  # If path has a file extension, it's likely a file
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)


def from_pb_param(data):
    drep = str(data)
    try:
        return float(drep)
    except ValueError:
        pass
    if drep.lower() in ["true", "false"]:
        return drep.lower() == "true"
    return drep
