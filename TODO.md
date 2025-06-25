# Pedalboard Pluginary - TODO List

## High Priority

### Code Cleanup
- [x] Create PLAN.md and TODO.md files
- [ ] Fix duplicate imports in scanner.py
- [ ] Remove redundant BaseScanner class definition
- [ ] Fix duplicate full_scan method in PedalboardScanner
- [ ] Remove obsolete scan_aufx_plugins and scan_vst3_plugins methods
- [ ] Clean up imports and organize them properly

### Type Safety
- [ ] Fix mypy errors in scanner.py
- [ ] Add proper type annotations for pedalboard imports
- [ ] Fix PedalboardPluginType alias usage
- [ ] Add Protocol definitions for plugin interfaces

### Critical Bugs
- [ ] Fix scanner initialization (missing ignores attribute)
- [ ] Fix scanner method calls in PedalboardScanner
- [ ] Ensure proper plugin loading with correct pedalboard API

## Medium Priority

### Async Support
- [ ] Create async versions of scanner classes
- [ ] Implement concurrent plugin scanning
- [ ] Add async file I/O operations
- [ ] Update CLI to support async operations

### Progress Callbacks
- [ ] Define progress callback protocol
- [ ] Add progress support to scanner classes
- [ ] Integrate tqdm for CLI progress
- [ ] Add cancellation support

### Caching
- [ ] Implement cache versioning
- [ ] Add cache validation on load
- [ ] Support incremental cache updates
- [ ] Add cache management CLI commands

### Error Handling
- [ ] Create custom exception classes
- [ ] Add proper error handling in scanners
- [ ] Implement retry logic for failures
- [ ] Improve error messages

## Low Priority

### Documentation
- [ ] Update README with new features
- [ ] Add API documentation
- [ ] Create usage examples
- [ ] Document configuration options

### Build and CI
- [ ] Set up GitHub Actions workflow
- [ ] Configure codecov integration
- [ ] Add pre-commit hooks
- [ ] Update build.sh script

### Testing
- [ ] Increase test coverage to 90%+
- [ ] Add integration tests
- [ ] Add performance benchmarks
- [ ] Test on Windows platform

## Future Enhancements
- [ ] Add plugin preset management
- [ ] Support for CLAP plugins
- [ ] Plugin categorization and tagging
- [ ] Export to different formats (CSV, etc.)
- [ ] Web UI for plugin management

## Notes
- Maintain backward compatibility
- Focus on reliability over features
- Keep dependencies minimal
- Ensure cross-platform compatibility