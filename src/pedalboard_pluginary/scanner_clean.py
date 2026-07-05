#!/usr/bin/env python3
# this_file: src/pedalboard_pluginary/scanner_clean.py

"""Clean scanner wrapper that suppresses all plugin output."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

# Store original stderr
_original_stderr = sys.stderr


@contextmanager
def suppress_all_output() -> Iterator[None]:
    """Aggressively suppress all output including OS-level stderr."""
    # Save original file descriptors
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    old_stdout_fd = os.dup(1)
    old_stderr_fd = os.dup(2)

    try:
        # Create null device
        devnull = open(os.devnull, "w")

        # Replace Python-level stdout/stderr
        sys.stdout = devnull
        sys.stderr = devnull

        # Replace OS-level stdout/stderr
        os.dup2(devnull.fileno(), 1)
        os.dup2(devnull.fileno(), 2)

        yield

    finally:
        # Restore OS-level descriptors
        os.dup2(old_stdout_fd, 1)
        os.dup2(old_stderr_fd, 2)
        os.close(old_stdout_fd)
        os.close(old_stderr_fd)

        # Restore Python-level stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        # Close devnull
        devnull.close()


def clean_scan(scanner_class: type[Any], *args: Any, **kwargs: Any) -> Any:
    """Run scanner with all output suppressed."""
    with suppress_all_output():
        scanner = scanner_class(*args, **kwargs)
        scanner.scan()
    return scanner
