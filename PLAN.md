# Pedalboard Pluginary - Essential Improvements Plan

## Overview

The failsafe scanning architecture has been fully implemented and tested, providing a robust and resumable scanning process. The codebase has been significantly cleaned up and streamlined, with all deprecated code removed and modules properly consolidated.

## Phase 1: Solidify Failsafe Scanning Architecture ✅ COMPLETED (2025-08-05)

### 1.1. Comprehensive Integration Testing
**Goal**: Ensure the new journaling and resumable scanning architecture is flawless under various failure conditions.
**Actions**:
- **Simulate Worker Crashes**: Write an integration test where the `scan_single.py` process is abruptly terminated (e.g., using `os.kill`). Verify that the main scanner correctly marks the plugin as `failed` or `timeout` in the journal and that the scan can be resumed.
- **Simulate Main Process Crash**: Write a test that kills the main `IsolatedPedalboardScanner` process mid-scan. On re-running the scan, verify that it correctly resumes from the journal and only processes pending plugins.
- **Test Atomic Commit**: Write a test to simulate a crash *during* the commit phase (after the journal is read but before the main cache is written). Verify that the main cache remains untouched and the journal is preserved, allowing the commit to be re-attempted on the next run.
- **Test Edge Cases**: Test with an empty journal, a journal with only failed plugins, and a journal from a fully completed but uncommitted scan.

## Phase 2: Code Organization & Cleanup ✅ COMPLETED (2025-08-05)

### 2.1. Module Consolidation
**Goal**: Reduce complexity and improve maintainability by merging related modules.
**Actions**:
- **Merge `scanner_isolated.py` and `journal.py`**: The `ScanJournal` is tightly coupled to the `IsolatedPedalboardScanner`. Merge the `ScanJournal` class into the `scanner_isolated.py` module to create a single, self-contained, and cohesive scanning unit.
- **Consolidate Cache Backends**: The `cache` sub-package can be simplified. The `SQLiteCacheBackend` is now the primary backend. The `json_backend.py` and `migration.py` can be deprecated or moved to a `legacy` sub-folder if backward compatibility is desired, otherwise removed.
- **Merge `json_utils.py` into `serialization.py`**: The `json_utils.py` was a temporary fix for a circular import. Now that the code is being reorganized, these functions can be moved back into `serialization.py`.

### 2.2. Remove Deprecated Code
**Goal**: Eliminate all obsolete code to create a clean and modern codebase.
**Actions**:
- **Remove `BaseScanner` and `AsyncScanner`**: The `IsolatedPedalboardScanner` is now the sole scanning implementation. The `base_scanner.py` and `async_scanner.py` modules, along with the `BaseScanner` class and `AsyncScannerMixin`, are no longer needed.
- **Remove Old Protocols**: The `protocols.py` file may contain protocols that are no longer relevant with the simplified architecture. Review and remove any that are not in use.
- **Clean up `__main__.py`**: The CLI is now based on `click`. Remove any remnants of the old `fire`-based CLI.

### 2.3. Optimize Imports and Structure
**Goal**: Ensure a clean and consistent import structure across the project.
**Actions**:
- **Standardize Imports**: Use a consistent import order (standard library, third-party, first-party) across all modules.
- **Use `__future__.annotations`**: Ensure all files have `from __future__ import annotations`.
- **Refactor `data.py`**: This module contains a mix of functions. Refactor it to be more focused on data path management.

## Next Steps

1.  **Immediate**: Begin Phase 1: Comprehensive Integration Testing.
2.  **Week 1**: Complete all integration tests for the failsafe scanning architecture.
3.  **Week 2**: Begin Phase 2: Code Organization & Cleanup.
4.  **Week 3**: Complete the module consolidation and remove all deprecated code.
5.  **Week 4**: Finalize the import optimization and refactor the `data.py` module.