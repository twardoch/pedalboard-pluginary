#!/usr/bin/env python3
import fire
from .core import PedalboardPluginary
from .scanner import PedalboardScanner
from benedict import benedict as bdict


def scan_plugins(extra_folders=None):
    if extra_folders:
        extra_folders = extra_folders.split(",")
    PedalboardScanner().rescan(extra_folders=None)


def update_plugins(extra_folders=None):
    if extra_folders:
        extra_folders = extra_folders.split(",")
    PedalboardScanner().update(extra_folders=None)


def list_json():
    return bdict(PedalboardPluginary().plugins).to_json()


def list_yaml():
    return bdict(PedalboardPluginary().plugins).to_yaml()


def cli():
    fire.core.Display = lambda lines, out: print(*lines, file=out)
    fire.Fire(
        {
            "scan": scan_plugins,
            "update": update_plugins,
            "list": list_json,
            "json": list_json,
            "yaml": list_yaml,
        }
    )


if __name__ == "__main__":
    cli()
