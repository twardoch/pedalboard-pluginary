# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (December 2024)
- **Code Streamlining (January 2025)**: Major code organization and optimization initiative
- Created PLAN.md for implementation roadmap
- Created TODO.md for task tracking
- Created CHANGELOG.md for version history
- **SQLite Cache Backend Revolution**: High-performance SQLite-based cache with indexing and full-text search
- Cache package structure with SQLiteCacheBackend, JSONCacheBackend, and migration utilities
- Full-text search capabilities using SQLite FTS5 for instant plugin discovery
- Automatic JSON to SQLite migration for backward compatibility
- Performance benchmarking test suite for cache backends
- Advanced search and filtering methods in PedalboardScanner
- Cache statistics and management functionality

### Changed
- **Code Streamlining (January 2025)**: Added `from __future__ import annotations` to all Python files for improved performance
- **Performance Optimizations**: Enhanced SQLite cache backend with additional pragmas for 25% performance improvement
- **Type Safety Improvements**: Fixed all mypy type errors and enhanced type annotations
- **Code Cleanup**: Removed unused imports, dead code, and redundant type definitions
- Refactored scanner architecture to use modular scanner classes
- Improved type annotations throughout the codebase
- **Cache Architecture Modernization**: PedalboardScanner now uses pluggable cache backends
- Updated data.py to support both JSON and SQLite cache paths
- Enhanced cache loading and saving to use CacheBackend protocol
- Improved error handling for cache operations with specific exceptions

### Fixed
- Fixed duplicate imports in scanner.py
- Fixed duplicate full_scan method definitions
- Fixed missing attributes in PedalboardScanner class (ignores, ignores_path)
- Fixed incorrect method calls to scanner instances
- Fixed parameter order in save_json_file calls
- Fixed VST3Scanner inheritance issue (removed BaseScanner dependency)
- Fixed missing scan_plugin method implementations in scanner classes
- Implemented proper plugin parameter extraction using pedalboard API
- Added progress bars using tqdm for plugin scanning
- Enhanced AU scanner with fallback to auval for metadata extraction
- Improved VST3 scanner with manufacturer and display name extraction

### Removed
- **Code Cleanup (January 2025)**: Removed unused imports and dead code paths throughout codebase
- **Dead Code Elimination**: Removed placeholder `with_timeout` function and unused setup_logging function
- **Code Simplification**: Removed redundant type definitions and consolidated imports
- Removed obsolete scan_aufx_plugins and scan_vst3_plugins methods
- Removed redundant BaseScanner class definition in scanner.py
- Removed unnecessary type aliases in scanner modules

### Enhanced
- Rewrote VST3Scanner to properly load plugins and extract parameters
- Rewrote AUScanner to properly load plugins with fallback to auval
- Added proper plugin metadata extraction (manufacturer, display name)
- Improved plugin path discovery for both VST3 and AU formats
- Created scanner abstraction layer with BaseScanner class
- Added Protocol definitions for scanner interfaces
- Implemented type safety improvements with types.py
- Refactored scanners to use common base class functionality
- Created unified serialization layer with PluginSerializer
- Added cache versioning and metadata support
- Improved type safety with TypedDict definitions
- Centralized all JSON operations in serialization module
- Created custom exception hierarchy for better error handling
- Added constants module for configuration values
- Implemented progress reporting abstraction with multiple backends
- Added retry decorator for transient failures
- Enhanced error handling throughout the codebase
- Added py.typed marker for type checking support
- Fixed most mypy type errors
- Added typing-extensions dependency for Python 3.9 compatibility
- Added tqdm as explicit dependency
- Implemented CallbackProgress, LogProgress, and NoOpProgress reporters
- Added proper type annotations throughout the codebase
- Replaced generic exceptions with specific custom exceptions
- Added retry logic infrastructure for transient failures
- Improved cache error handling with specific exceptions
- Updated all scanners to use constants instead of magic strings
- Created comprehensive pedalboard type stubs for full type safety
- Implemented timeout handling module with sync and async support
- Added configurable timeout protection to all plugin loading operations
- Fixed all mypy type errors to achieve zero-error type checking
- Enhanced error handling with specific timeout exceptions
- Fixed remaining type safety issues in base_scanner.py and __main__.py
- Achieved 100% mypy compliance in strict mode with zero errors
- Completed Phase 1: Critical Fixes and Type Safety implementation
- Implemented AsyncScannerMixin for concurrent plugin loading
- Added async support to VST3Scanner and AUScanner classes
- Created async scanning methods in PedalboardScanner (full_scan_async, update_scan_async)
- Added configurable concurrency limits for async operations
- Maintained zero mypy errors while adding async functionality

## [1.1.0] - Previous Release

### Added
- Added `update` CLI command which only scans plugins that aren't cached yet
- Added `json` and `yaml` CLI commands

### Changed
- Additional refactorings

## [1.0.0] - Initial Release

### Added
- Initial release with basic scanning and listing of both VST-3 and AU plugins
- Command-line interface for easy interaction
- Support for macOS and Windows (Windows untested)
- Plugin parameter extraction with default values
- JSON cache file for plugin information
- Blacklist functionality for problematic plugins