# Pedalboard Pluginary - PLAN

## Status

The 2026-07-05 modernization pass is complete: dependencies are honest, the CLI
entry point works, ruff and mypy are clean, the test suite is repaired and fully
mocked (77 passing), CI/release workflows are in place, and the docs match the
shipped code. See `CHANGELOG.md` for the detail and `TODO.md` for the flat task list.

## Remaining work

### Phase 1 — Coverage and benchmark
- Measure coverage with `pytest-cov` and lift to 80%+. The thinnest spots are
  `cache/sqlite_backend.py` and `scan_single.py`.
- Turn the 289-plugin scan referenced in `CLAUDE.md` into a benchmark test that
  is skipped by default (no plugins on CI) but runnable locally with a marker.

### Phase 2 — Dead-code audit
- Confirm whether `scanner_clean.py`, `cache/json_backend.py`, and
  `cache/migration.py` are still referenced. If the SQLite-only migration is
  final, remove them and their tests in one commit.

### Phase 3 — Small correctness follow-ups
- Replace `datetime.utcnow()` (deprecated) in `serialization.py` with
  `datetime.now(datetime.UTC)`.
- Consider adaptive per-plugin timeouts using the journal's recorded scan times.

### Phase 4 — Features (larger, optional)
- Plugin categorisation/tagging and preset management, as originally sketched.
