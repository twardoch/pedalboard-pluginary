#!/usr/bin/env python3
import fire
from .core import PedalboardPluginary
from .scanner import PedalboardScanner

def scan_plugins():
    PedalboardScanner().scan()

def list_plugins():
    return PedalboardPluginary().list_plugins()

def cli():
    fire.core.Display = lambda lines, out: print(*lines, file=out)
    fire.Fire({
        'scan': scan_plugins,
        'list': list_plugins
    })

if __name__ == "__main__":
    cli()
