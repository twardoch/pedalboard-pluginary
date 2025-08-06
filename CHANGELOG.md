# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed (2025-08-06)
- **SQLite as Primary Storage**: Fully migrated to SQLite as the sole storage backend
  - Removed dependency on JSON file storage for plugin data
  - SQLite now provides ACID guarantees and better performance
  - JSON export/import now only used for data interchange
  - Eliminated confusion between storage backends
  - Cache backend now exclusively uses SQLite with full-text search

### Fixed (2025-08-06)
- **Critical Scanner Fixes**: Resolved major issues preventing plugin storage
  - Fixed journal database connection issues (removed thread-local storage)
  - Resolved SQLite "readonly database" errors with proper commit operations
  - Fixed plugin ID consistency between scan_single.py and journal operations
  - Corrected journal recreation after rescan to prevent crashes
  - Fixed scanner to properly check SQLite for existing plugins
  - Added missing SQLite backend methods (get_all_plugins, get_cached_paths)
  - Successfully scanned and stored 289 plugins in SQLite database

### Fixed (2025-08-06)
- **Scanner Bug Fixes**: Fixed critical issues in isolated scanner architecture
  - Fixed duplicate journal initialization in scanner_isolated.py 
  - Removed redundant journal path assignment that was overwriting configured path
  - Fixed plugin_id generation in scan_single.py to match expected format
  - Updated parameter extraction to use correct SerializedParameter format
  - Fixed metadata handling to align with SerializedPlugin model structure
  - Corrected plugin_type field naming for consistency across the codebase

### Added (2025-08-05)
- **Comprehensive Integration Tests**: Complete test suite for failsafe scanning architecture
  - Worker process crash simulation tests  
  - Main process crash and resume verification
  - Commit phase crash protection tests
  - Edge case handling (empty journal, all-failed journal)
  - Concurrent journal access tests
  - Real subprocess termination tests

### Changed (2025-08-05)  
- **Major Code Reorganization**: Streamlined and consolidated codebase
  - Merged ScanJournal class into scanner_isolated.py for better cohesion
  - Consolidated json_utils.py functions into serialization.py
  - Removed all deprecated scanner implementations (base_scanner.py, async_scanner.py)
  - Removed unused scanner modules (vst3_scanner.py, au_scanner.py)
  - Cleaned up protocols.py by removing unused PluginScanner protocol
  - Replaced fire with argparse in scan_single.py for consistency
  - Added `from __future__ import annotations` for Python 3.7+ compatibility
  - Fixed import issues and circular dependencies

### Fixed (2025-08-05)
- Fixed missing thread-local storage initialization in ScanJournal class
- Fixed import errors in __init__.py after scanner refactoring

### Added (August 2025)
- **Failsafe Scanning Architecture**: Implemented a transactional and resumable scanning architecture.
  - Created `journal.py` with a `ScanJournal` class for robustly storing scan progress.
  - The individual plugin scanner (`scan_single.py`) is now journal-aware, persisting its own results.
  - The main scanner orchestrator (`scanner_isolated.py`) is now fully resumable, and atomically commits results.
  - The CLI has been migrated to `click` and simplified to use the new, robust scanning mechanism.

### Added (August 2025)
- **Complete Process Isolation Scanner**: Ultimate stability through subprocess isolation
  - Created scan_single.py standalone CLI tool that loads one plugin and returns JSON
  - Each plugin scanned in completely separate process - crashes don't affect scanner
  - IsolatedPedalboardScanner orchestrates subprocess calls safely
  - Parallel execution via ThreadPoolExecutor for optimal performance
  - Configurable timeout (default 30 seconds) per plugin
  - Graceful handling of plugin crashes, timeouts, and errors
  - Default scanner mode is now isolated for maximum stability
  - New scanner modules: scanner_isolated.py, scanner_parallel.py, scanner_worker.py, scanner_clean.py
  - Created modular scanner architecture with BaseScanner class

### Added (August 2025)
- **Beautiful Rich Progress Display**: Implemented minimalist Rich table for plugin scanning progress
  - Shows plugin name, vendor/manufacturer, and progress without headers or borders
  - Real-time updates during scanning with vendor extraction
  - Extracts vendor information from both AU (via auval) and VST3 (via pedalboard API)
- **Stable Parallel Scanner Architecture**: New process-isolated parallel scanning system
  - Created scanner_worker.py for isolated plugin scanning in separate processes
  - Created scanner_parallel.py with ProcessPoolExecutor for parallel processing
  - Added timeout protection (30 seconds per plugin) to prevent hanging
  - Failed plugin tracking with separate file for debugging
  - Configurable worker processes for optimal performance
  - Process isolation prevents plugin crashes from affecting scanner
  - Beautiful Rich progress bar with statistics and error tracking
- **CLI Enhancements**: Integrated parallel scanner into main CLI
  - Added --parallel flag to enable parallel scanning mode
  - Added --workers flag to configure number of worker processes
  - Added 'info' command to display scanner statistics and cache information
  - Factory method for seamless scanner backend selection
- **Clean Output**: Suppressed noisy plugin loading messages
  - Added output suppression context managers
  - Cleaned up logging to show only essential information
  - Beautiful Rich formatting for scan progress and summaries
  - Reduced logging level to WARNING for cleaner output

### Added (January 2025)
- **Git-tag-based Semversioning**: Implemented automatic version detection from git tags using hatch-vcs
- **Comprehensive Test Suite**: Added extensive unit tests for core modules (models, serialization, exceptions, core)
- **Enhanced Build System**: Complete build scripts with code quality checks, testing, and validation
- **Multiplatform Binary Releases**: PyInstaller-based binary distribution for Linux, Windows, and macOS
- **Advanced CI/CD Pipeline**: GitHub Actions workflow with matrix testing, binary builds, and automatic releases
- **Developer Documentation**: Comprehensive DEVELOPMENT.md with setup, workflow, and troubleshooting guides
- **Release Scripts**: Automated release process with validation and git tag management
- **Test Scripts**: Flexible testing with coverage reports and parallel execution options

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