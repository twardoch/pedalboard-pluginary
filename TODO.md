# Pedalboard Pluginary - Essential Improvements TODO

## ✅ Phase 1: Solidify Failsafe Scanning Architecture - COMPLETED (2025-08-05)

### Comprehensive Integration Testing
- [x] Write integration test to simulate a worker process crash.
- [x] Write integration test to simulate a main process crash and verify resume.
- [x] Write integration test to simulate a crash during the commit phase.
- [x] Write integration tests for edge cases (empty journal, all-failed journal).

## ✅ Phase 2: Code Organization & Cleanup - COMPLETED (2025-08-05)

### Module Consolidation
- [x] Merge the `ScanJournal` class into the `scanner_isolated.py` module.
- [x] Merge the contents of `json_utils.py` into `serialization.py` and remove `json_utils.py`.

### Remove Deprecated Code
- [x] Remove `base_scanner.py` and `async_scanner.py`.
- [x] Review and remove any unused protocols in `protocols.py`.
- [x] Remove any remaining `fire`-based CLI code from `__main__.py`.

### Optimize Imports and Structure
- [x] Standardize import order across all modules.
- [x] Ensure all files have `from __future__ import annotations`.

## Next Steps

- [ ] Full integration testing with real plugins
- [ ] Performance benchmarking
- [ ] Documentation updates
- [ ] Refactor `data.py` to focus on data path management
- [ ] Consider deprecating or removing `json_backend.py` and `migration.py` modules
