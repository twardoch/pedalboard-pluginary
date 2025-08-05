#!/usr/bin/env python3
# this_file: src/pedalboard_pluginary/scanner_clean.py

"""Clean scanner wrapper that suppresses all plugin output."""

import os
import sys
import tempfile
from contextlib import contextmanager

# Store original stderr
_original_stderr = sys.stderr


@contextmanager
def suppress_all_output():
    """Aggressively suppress all output including OS-level stderr."""
    # Save original file descriptors
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    old_stdout_fd = os.dup(1)
    old_stderr_fd = os.dup(2)
    
    try:
        # Create null device
        devnull = open(os.devnull, 'w')
        
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


def clean_scan(scanner_class, *args, **kwargs):
    """Run scanner with all output suppressed."""
    with suppress_all_output():
        scanner = scanner_class(*args, **kwargs)
        scanner.scan()
    return scanner