# Pedalboard Pluginary - TODO

## Current Focus

### Performance & Optimization
- [ ] Performance benchmarking of scan operations with 1000+ plugins
- [ ] Optimize journal database operations for large plugin collections
- [ ] Implement adaptive timeout based on plugin complexity
- [ ] Add plugin scan retry mechanism for transient failures

### Documentation
- [ ] Update README.md with new isolated scanner architecture
- [ ] Document journaling system and crash recovery features
- [ ] Add API documentation for scanner_isolated module
- [ ] Create user guide for CLI commands
- [ ] Document SQLite storage architecture

### Code Quality
- [ ] Refactor `data.py` to focus on data path management
- [ ] Remove deprecated `json_backend.py` and `migration.py` modules
- [ ] Add type hints to remaining untyped functions
- [ ] Improve error messages and user feedback
- [ ] Clean up unused scanner modules (scanner_clean.py, etc.)

### Testing
- [ ] Add unit tests for ScanJournal class
- [ ] Create performance regression tests
- [ ] Test cross-platform compatibility (Windows, Linux)
- [ ] Add tests for edge cases in plugin parameter extraction
- [ ] Test concurrent scanning with multiple workers

### Features
- [ ] Add plugin preset management functionality
- [ ] Implement plugin categorization and tagging
- [ ] Add export functionality for different DAW formats
- [ ] Create web UI for plugin browser
- [ ] Add plugin search with full-text capabilities

## Completed (2025-08-06)

- [x] Fixed scanner to use SQLite as primary storage
- [x] Removed JSON storage dependencies
- [x] Fixed journal database connection issues
- [x] Resolved plugin ID consistency problems
- [x] Successfully implemented SQLite-only storage (289 plugins tested)
- [x] Full integration testing with real plugins

## Completed (2025-08-05)

See CHANGELOG.md for Phase 1 and Phase 2 completion details.