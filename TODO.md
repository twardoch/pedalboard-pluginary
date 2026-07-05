# Pedalboard Pluginary - TODO

## Done (2026-07-05 modernization pass)

- [x] Declare real deps (add click, rich; drop fire, python-benedict); fix entry point
- [x] Switch to ruff + mypy; `ruff check` and `mypy` clean
- [x] Add CI (ruff/mypy/pytest, py3.10–3.12) and release (PyPI-on-tag) workflows; add build.sh
- [x] Fix Linux cache path to honour XDG_CACHE_HOME
- [x] Consolidate duplicate TimeoutError into the exception hierarchy
- [x] Repair the test suite; mock plugin scanning; 77 tests pass
- [x] Rewrite README against the current API; add Jekyll docs/

## Next

### Tests & coverage
- [ ] Measure coverage and lift to 80%+ (sqlite_backend and scan_single are thin)
- [ ] Codify the 289-plugin benchmark from CLAUDE.md as a (skippable) benchmark test

### Code quality
- [ ] Remove dead modules if confirmed unused (scanner_clean.py, json_backend.py, migration.py)
- [ ] Replace `datetime.utcnow()` in serialization.py with timezone-aware `datetime.now(UTC)`

### Features
- [ ] Plugin categorisation and tagging
- [ ] Preset management
- [ ] Adaptive per-plugin timeout based on prior scan time
