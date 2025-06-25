# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Created PLAN.md for implementation roadmap
- Created TODO.md for task tracking
- Created CHANGELOG.md for version history

### Changed
- Refactored scanner architecture to use modular scanner classes
- Improved type annotations throughout the codebase

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