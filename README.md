# Pedalboard Pluginary

[![PyPI version](https://badge.fury.io/py/pedalboard-pluginary.svg)](https://badge.fury.io/py/pedalboard-pluginary)
[![Python versions](https://img.shields.io/pypi/pyversions/pedalboard-pluginary.svg)](https://pypi.org/project/pedalboard-pluginary/)
[![Build Status](https://github.com/twardoch/pedalboard-pluginary/actions/workflows/ci.yml/badge.svg)](https://github.com/twardoch/pedalboard-pluginary/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/twardoch/pedalboard-pluginary/branch/main/graph/badge.svg)](https://codecov.io/gh/twardoch/pedalboard-pluginary)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Pedalboard Pluginary** is an independent, high-performance Python package and command-line tool designed to scan, list, and manage VST3 and Audio Unit (AU) audio plugins. It serves as an invaluable companion for the [_Pedalboard_](https://github.com/spotify/pedalboard) library by Spotify, empowering developers and audio professionals to interact with their plugin collections programmatically. While intended to complement _Pedalboard_, it is not affiliated with _Pedalboard_ or Spotify.

## Table of Contents

*   [What is Pedalboard Pluginary?](#what-is-pedalboard-pluginary)
*   [Who is it For?](#who-is-it-for)
*   [Why is it Useful?](#why-is-it-useful)
*   [Recent Improvements](#recent-improvements)
*   [Installation](#installation)
*   [Command-Line Usage](#command-line-usage)
    *   [Scan for Plugins](#scan-for-plugins)
    *   [List and Search Plugins](#list-and-search-plugins)
    *   [Get Plugin Information](#get-plugin-information)
    *   [Manage Cache](#manage-cache)
*   [Python Library Usage](#python-library-usage)
*   [Future Plans](#future-plans)
*   [Technical Details](#technical-details)
    *   [Core Architecture](#core-architecture)
    *   [Code Structure](#code-structure)
    *   [Key Technologies & Libraries](#key-technologies--libraries)
    *   [Coding Conventions & Standards](#coding-conventions--standards)
    *   [Contributing Guidelines](#contributing-guidelines)
    *   [Testing](#testing)
*   [Changelog Highlights](#changelog-highlights)
*   [License](#license)
*   [Authors](#authors)

## What is Pedalboard Pluginary?

In the world of digital audio, plugins (like equalizers, reverbs, synthesizers) are essential tools. Pedalboard Pluginary helps you bridge the gap between your Python projects and your audio plugin arsenal. It meticulously scans your system, identifying installed VST3 (on macOS, Windows, and Linux) and Audio Unit (AU) plugins (on macOS). It then catalogs them, extracting crucial information like their names, paths, and even their default parameters.

**Key Features:**

*   **Comprehensive Plugin Scanning:** Automatically discovers VST3 and AU plugins in standard system locations and user-specified folders.
*   **High-Performance Engine:** Features an advanced asynchronous scanning engine for significantly faster discovery, especially with large plugin libraries.
*   **Robust Caching:** Utilizes an SQLite database by default for efficient storage and quick retrieval of plugin information, including indexed search and full-text search capabilities. Legacy JSON cache support with automatic migration is also included.
*   **Detailed Parameter Introspection:** Leverages the _Pedalboard_ library to access and list the default parameters of each plugin.
*   **Modern Command-Line Interface (CLI):** Offers a user-friendly CLI built with Click and Rich for easy interaction, searching, and management of your plugin library.
*   **Python Library:** Easily integrate plugin scanning and listing into your Python scripts and applications.
*   **Problematic Plugin Handling:** Includes a mechanism (`ignores.json`) to "blacklist" plugins known to cause issues, ensuring smoother operation.
*   **Cross-Platform:** Supports macOS (VST3, AU), Windows (VST3), and Linux (VST3). Requires Python 3.9+.

## Who is it For?

Pedalboard Pluginary is built for:

*   **Python Developers:** Working on audio applications, batch processing, or tools that need to interact with audio plugins.
*   **Audio Engineers & Music Producers:** Who want to programmatically manage or query their plugin collections, or automate audio workflows involving plugins.
*   **Researchers:** In audio signal processing or music information retrieval who need access to plugin metadata.
*   **Anyone using the Pedalboard library:** Who needs a reliable way to discover and list available plugins for use with Pedalboard.

## Why is it Useful?

Managing a large collection of audio plugins can be challenging. Pedalboard Pluginary simplifies this by:

*   **Automating Discovery:** No more manual searching for plugin paths.
*   **Providing Programmatic Access:** Use Python to get lists of plugins, their parameters, and other metadata, enabling automation and custom tooling.
*   **Enhancing Workflow with Pedalboard:** Easily find and identify plugins you want to load and use with the Pedalboard library.
*   **Boosting Performance:** The async scanning and SQLite cache ensure that even extensive plugin libraries are handled quickly and efficiently.
*   **Offering Powerful Search:** The CLI allows for quick filtering and searching of your plugin catalog.

## Recent Improvements

Pedalboard Pluginary has undergone significant enhancements to boost performance and scalability:

*   **Asynchronous Scanning:** Massively parallelized plugin scanning reduces scan times dramatically, especially for large libraries.
*   **SQLite Cache Backend:** The default cache now uses SQLite, offering indexed search, full-text search, and much better performance for large datasets compared to the previous JSON cache. Automatic migration from old JSON caches is supported.
*   **Modernized CLI (Planned/In Progress):** The command-line interface is being updated using Click and Rich for a more powerful, user-friendly experience with better help and output formatting (details below reflect this new interface).
*   **Enhanced Type Safety:** The codebase is strictly typed and checked with mypy, improving reliability.

## Installation

You can install Pedalboard Pluginary using pip:

```bash
python3 -m pip install --upgrade pedalboard-pluginary
```

For the latest development version:

```bash
python3 -m pip install --upgrade git+https://github.com/twardoch/pedalboard-pluginary
```
Requires Python 3.9 or newer.

## Command-Line Usage

Pedalboard Pluginary provides a powerful and user-friendly command-line interface (`pbpluginary`).

*(Note: The CLI is being actively developed. The commands below reflect the intended modern interface based on Click and Rich, as outlined in the project's development plan. Some commands/options might differ slightly if you're on an older version.)*

Here are some common commands:

### Scan for Plugins

*   **Scan all plugins (default: async, SQLite cache):**
    ```bash
    pbpluginary scan
    ```
*   **Force a full rescan, ignoring existing cache:**
    ```bash
    pbpluginary scan --force
    ```
*   **Scan synchronously:**
    ```bash
    pbpluginary scan --sync
    ```
*   **Scan additional custom folders:**
    ```bash
    pbpluginary scan --folders "/path/to/my/vst3s,/another/path/to/plugins"
    ```
*   **Adjust concurrency for async scanning:**
    ```bash
    pbpluginary scan --concurrency 20
    ```

### List and Search Plugins

*   **List all discovered plugins (default: table format):**
    ```bash
    pbpluginary list
    ```
*   **List plugins in JSON format:**
    ```bash
    pbpluginary list --format json
    ```
*   **Filter plugins by name or manufacturer (full-text search):**
    ```bash
    pbpluginary list --filter "Reverb"
    ```
*   **Filter by plugin type (VST3 or AU):**
    ```bash
    pbpluginary list --type vst3
    ```
*   **Filter by manufacturer:**
    ```bash
    pbpluginary list --manufacturer "FabFilter"
    ```
*   **Advanced search (combines with list filters or uses dedicated `search`):**
    ```bash
    pbpluginary search "Equalizer" --type au
    pbpluginary search "Pro-Q" --fuzzy # Fuzzy search for approximate matches
    ```

### Get Plugin Information

*   **Show detailed information for a specific plugin by its ID:**
    ```bash
    pbpluginary info "vst3/FabFilter Pro-Q 3"
    ```
    *(Plugin IDs are typically `type/filename_stem`, e.g., `vst3/MassiveX` or `aufx/ChannelEQ`)*
*   **Test if a plugin can be loaded:**
    ```bash
    pbpluginary info "vst3/Serum" --test
    ```

### Manage Cache

*   **View cache statistics:**
    ```bash
    pbpluginary cache stats
    ```
*   **Clear the plugin cache:**
    ```bash
    pbpluginary cache clear
    ```
*   **Attempt to repair a corrupted cache:**
    ```bash
    pbpluginary cache repair
    ```
*   **Migrate cache format (e.g., from a legacy JSON cache to SQLite):**
    ```bash
    pbpluginary cache migrate --to sqlite
    ```

For a full list of commands and options, use:
```bash
pbpluginary --help
pbpluginary <command> --help
```

## Python Library Usage

You can also use Pedalboard Pluginary as a library in your Python scripts.

**Basic Example:**

```python
from pedalboard_pluginary import PedalboardPluginary
from pedalboard_pluginary.config import PluginaryConfig, CacheConfig, ScanConfig # For customization
from pedalboard_pluginary.cache import SQLiteCacheBackend # or JSONCacheBackend
from pedalboard_pluginary.progress import TqdmProgress # or LogProgress, NoOpProgress
import asyncio # Required for async scanning

# For default behavior (async scanning, SQLite cache, TQDM progress)
# The PedalboardPluginary constructor can take a config object or individual backend/reporter instances.
pluginary_scanner = PedalboardPluginary()

# Perform a scan. By default, this will load from cache if available and up-to-date,
# or perform an async scan if needed.
# The scan() method intelligently decides whether to load or rescan.
# To force a full async rescan:
# plugins = asyncio.run(pluginary_scanner.full_scan_async())
# To force a full sync rescan:
# plugins = pluginary_scanner.full_scan()

# To load or scan as needed (recommended):
# If you want to ensure an async scan if data is missing/stale:
if not pluginary_scanner.cache_backend.exists(): # Or some other logic to check cache freshness
    print("Cache not found or stale, performing async scan...")
    plugins = asyncio.run(pluginary_scanner.full_scan_async())
else:
    print("Loading plugins from cache...")
    pluginary_scanner.load_data() # Loads from the backend specified in constructor
    plugins = pluginary_scanner.plugins

print(f"Found/loaded {len(plugins)} plugins.")

# List all VST3 plugins by FabFilter
fabfilter_vst3s = [
    p_info for p_info in plugins.values()
    if p_info.plugin_type == "vst3" and p_info.manufacturer and "FabFilter" in p_info.manufacturer
]

print("\\nFabFilter VST3 Plugins:")
for plugin in fabfilter_vst3s:
    print(f"  Name: {plugin.name}, Path: {plugin.path}")
    print(f"    Parameters ({len(plugin.parameters)}):")
    for param_name, param_details in list(plugin.parameters.items())[:3]: # Print first 3 params
        print(f"      - {param_name}: {param_details.value}")

# Get detailed information for a specific plugin by its ID
plugin_id_to_find = "vst3/FabFilter Pro-Q 3" # Example ID, adjust if not present
if plugin_id_to_find in plugins:
    pro_q3 = plugins[plugin_id_to_find]
    print(f"\\nDetails for {pro_q3.name}:")
    print(f"  Manufacturer: {pro_q3.manufacturer}")
    print(f"  Path: {pro_q3.path}")
else:
    print(f"\\nPlugin {plugin_id_to_find} not found in results.")

# More customized usage:
# Configure for synchronous scanning and JSON cache
config = PluginaryConfig(
    scan=ScanConfig(async_mode=False), # Configure scanning behavior
    cache=CacheConfig(backend="json")  # Specify cache type
)
custom_scanner = PedalboardPluginary(
    config=config,
    progress_reporter=LogProgress() # Use logging for progress feedback
)
# For sync scan:
custom_plugins = custom_scanner.full_scan()
print(f"\\nFound {len(custom_plugins)} plugins with custom synchronous settings (JSON cache).")

# Search for plugins (most effective with SQLite backend)
# Ensure you have scanned with SQLite backend first for these examples
if isinstance(pluginary_scanner.cache_backend, SQLiteCacheBackend):
    reverbs = pluginary_scanner.search_plugins(query="Reverb", limit=5)
    print("\\nFound reverbs (up to 5):")
    for reverb in reverbs:
        print(f"- {reverb.name} (Type: {reverb.plugin_type}, Manufacturer: {reverb.manufacturer or 'N/A'})")
else:
    print("\\nSearch examples are most effective with the SQLite backend (default).")

```

The main class you'll interact with is `PedalboardPluginary` (from `pedalboard_pluginary.__init__.py`, which imports from `pedalboard_pluginary.core`). It orchestrates the scanning process using specialized scanner classes (`VST3Scanner`, `AUScanner`) and manages the plugin data through cache backends (`SQLiteCacheBackend`, `JSONCacheBackend`). The `PluginInfo` and `PluginParameter` data models (from `pedalboard_pluginary.models`) represent the structured information about each plugin and its parameters.

## Future Plans

Pedalboard Pluginary is actively developed. Future enhancements may include:

*   **Plugin "Jobs":** A system to define and execute a stack of plugins with specific parameter values, useful for batch processing or applying plugin chains.
*   **Enhanced Plugin Categorization:** Intelligent categorization of plugins based on names, parameters, and other metadata.
*   **Configuration Management:** More robust configuration via files and environment variables.
*   **DAW Integration Helpers:** Utilities to facilitate interaction with Digital Audio Workstations.
*   **Plugin Preset System:** Support for saving and loading plugin parameter presets.

Stay tuned for more features!

## Technical Details

This section provides a deeper dive into how Pedalboard Pluginary works, its architecture, and guidelines for contributors.

### Core Architecture

Pedalboard Pluginary is designed with modularity, performance, and type safety in mind.

*   **Orchestration & Scanners:**
    *   The main `PedalboardPluginary` class (in `src/pedalboard_pluginary/core.py`) acts as the primary interface for library usage and orchestrates the scanning process.
    *   The `PedalboardScanner` class (in `src/pedalboard_pluginary/scanner.py`) manages the actual scanning logic, utilizing specialized scanner classes for different plugin types.
    *   `VST3Scanner` (in `src/pedalboard_pluginary/scanners/vst3_scanner.py`): Handles discovery and scanning of VST3 plugins across macOS, Windows, and Linux.
    *   `AUScanner` (in `src/pedalboard_pluginary/scanners/au_scanner.py`): Handles discovery and scanning of Audio Unit (AU) plugins on macOS, primarily using `auval` for discovery and `pedalboard` for introspection, with `auval` as a fallback.
    *   Scanners are built upon a `BaseScanner` (in `src/pedalboard_pluginary/base_scanner.py`) and adhere to `PluginScanner` protocols (defined in `src/pedalboard_pluginary/protocols.py`).

*   **Asynchronous Scanning:**
    *   To significantly improve performance, especially with large plugin libraries, Pedalboard Pluginary employs asynchronous scanning.
    *   The `AsyncScannerMixin` (in `src/pedalboard_pluginary/async_scanner.py`) provides core async capabilities using `asyncio`.
    *   Plugin loading, which can be I/O bound or CPU-bound (due to external processes), is offloaded to threads managed by `asyncio.get_event_loop().run_in_executor`.
    *   Concurrency is managed using `asyncio.Semaphore` to limit the number of plugins being processed simultaneously (configurable, defaults to 10, see `DEFAULT_MAX_CONCURRENT` in `src/pedalboard_pluginary/constants.py`).
    *   Timeout protection for individual plugin loading is implemented via `sync_timeout` and `async_timeout` utilities (from `src/pedalboard_pluginary/timeout.py`).

*   **Caching System:**
    *   **SQLite Backend (Default):** For optimal performance, scalability, and advanced querying, Pedalboard Pluginary defaults to an SQLite cache backend (`SQLiteCacheBackend` in `src/pedalboard_pluginary/cache/sqlite_backend.py`).
        *   Features indexed columns for fast lookups.
        *   Utilizes SQLite's Full-Text Search (FTS5) for efficient searching of plugin names and manufacturers.
        *   Stores plugin data as JSON blobs within the database.
        *   Designed to handle tens of thousands of plugins with minimal performance degradation.
        *   Includes performance pragmas (WAL mode, cache size adjustments) for speed and reliability.
    *   **JSON Backend (Legacy):** A legacy JSON-based cache (`JSONCacheBackend` in `src/pedalboard_pluginary/cache/json_backend.py`) is supported for backward compatibility.
    *   **Automatic Migration:** If an existing JSON cache is found and no SQLite cache is present, the tool will automatically attempt to migrate the data to the SQLite backend (`migrate_json_to_sqlite` in `src/pedalboard_pluginary/cache/migration.py`).
    *   **Cache Location:** Cache files are stored in a platform-specific user cache directory (e.g., `~/.cache/com.twardoch.pedalboard-pluginary/` on Linux, `~/Library/Application Support/com.twardoch.pedalboard-pluginary/` on macOS). This is managed by `get_cache_path` and `get_sqlite_cache_path` in `src/pedalboard_pluginary/data.py`.
    *   Both backends adhere to the `CacheBackend` protocol.

*   **Data Models & Serialization:**
    *   Plugin information is structured using dataclasses: `PluginInfo` for overall plugin metadata and `PluginParameter` for individual parameter details (defined in `src/pedalboard_pluginary/models.py`).
    *   A dedicated `PluginSerializer` (in `src/pedalboard_pluginary/serialization.py`) handles the conversion of these data models to and from dictionary representations suitable for JSON storage (either as standalone files or as JSON blobs in SQLite).
    *   TypedDicts (`SerializedPlugin`, `SerializedParameter` in `src/pedalboard_pluginary/types.py`) are used to ensure the structure of serialized data.
    *   Cache files include metadata such as cache version, creation/update timestamps, and scanner version for future compatibility and management.

*   **Plugin Introspection:**
    *   The actual loading of plugin binaries and introspection of their parameters is performed by the underlying [Spotify Pedalboard](https://github.com/spotify/pedalboard) library. Pedalboard Pluginary orchestrates the discovery and data handling around this core functionality.

*   **Ignoring Problematic Plugins:**
    *   A `default_ignores.json` file (in `src/pedalboard_pluginary/resources/`) contains a list of plugin identifiers known to cause issues with Pedalboard or scanning.
    *   Users can maintain their own `ignores.json` in the cache directory to extend this list. These plugins are skipped during scans.

*   **Error Handling & Resilience:**
    *   A custom exception hierarchy (`PluginaryError`, `ScannerError`, `CacheError`, etc., in `src/pedalboard_pluginary/exceptions.py`) provides granular error reporting.
    *   Retry logic with exponential backoff (`with_retry` decorator in `src/pedalboard_pluginary/retry.py`) is available for operations that might transiently fail.
    *   Timeout mechanisms protect against plugins that hang during loading.

### Code Structure

The project follows a standard Python source layout:

*   `src/pedalboard_pluginary/`: Main package directory.
    *   `__init__.py`: Package entry point, exports version and `PedalboardPluginary`.
    *   `cli.py`: (Intended location for Click-based CLI, as per `PLAN.md`). Current CLI logic is in `__main__.py`.
    *   `core.py`: Contains `PedalboardPluginary` class.
    *   `scanner.py`: Contains `PedalboardScanner` orchestrator.
    *   `async_scanner.py`: `AsyncScannerMixin` for concurrency.
    *   `base_scanner.py`: `BaseScanner` abstract class.
    *   `scanners/`: Specific plugin type scanners (`au_scanner.py`, `vst3_scanner.py`).
    *   `cache/`: Cache backends (`sqlite_backend.py`, `json_backend.py`, `migration.py`).
    *   `models.py`: Dataclasses (`PluginInfo`, `PluginParameter`).
    *   `serialization.py`: `PluginSerializer`.
    *   `protocols.py`: Interface definitions.
    *   `exceptions.py`: Custom exceptions.
    *   `constants.py`: Global constants.
    *   `types.py`: TypedDicts and type aliases.
    *   `utils.py`: Utility functions.
    *   `progress.py`: Progress reporting classes.
    *   `retry.py`: Retry decorators.
    *   `timeout.py`: Timeout utilities.
    *   `config.py`: (As per `PLAN.md`) Pydantic-based configuration management.
    *   `resources/default_ignores.json`: Default blacklist for plugins.
*   `src/pedalboard-stubs/`: Type stubs for `pedalboard` library.
*   `tests/`: Pytest tests.
*   `pyproject.toml`: Project configuration, dependencies, and tool settings.
*   `PLAN.md`: Detailed development plan, often reflecting the most current architectural design.

### Key Technologies & Libraries

*   **Python 3.9+**
*   **Core Functionality:**
    *   [Pedalboard](https://github.com/spotify/pedalboard): For loading plugins and introspecting parameters.
    *   `sqlite3`: For the default SQLite cache backend.
    *   `asyncio`: For concurrent plugin scanning.
*   **Command-Line Interface (CLI):**
    *   [Click](https://click.palletsprojects.com/): For building the modern, user-friendly CLI (primary CLI framework).
    *   [Rich](https://rich.readthedocs.io/): For beautiful and informative terminal output.
*   **Utilities:**
    *   `tqdm`: For progress bars during scanning.
    *   `PyYAML`: For YAML output in the CLI.
*   **Development & Testing:**
    *   `pytest`, `pytest-cov`
    *   `mypy` (run in strict mode)
    *   `black`, `isort`, `flake8`
    *   `hatchling` (for building)
    *   `typing-extensions` (for older Python versions)

### Coding Conventions & Standards

*   **Type Safety:** The project aims for full type safety using Python's type hinting and is checked with `mypy` in strict mode. See `pyproject.toml` for `mypy` configuration.
*   **Code Style:** Code is formatted using Black and isort. Flake8 is used for linting. These are enforced via pre-commit hooks (see `.pre-commit-config.yaml`).
*   **Pythonic Code:** Adherence to idiomatic Python practices is encouraged.
*   **Modularity:** Functionality is broken down into logical modules and classes, often using protocols for defining interfaces.

### Contributing Guidelines

Contributions are welcome! Please follow these guidelines:

1.  **Reporting Issues:**
    *   If you encounter bugs, have feature requests, or suggestions, please open an issue on the [GitHub Issues page](https://github.com/twardoch/pedalboard-pluginary/issues).
    *   Provide detailed information, including steps to reproduce, error messages, your operating system, and relevant versions.

2.  **Contributing Code:**
    *   Fork the repository on GitHub.
    *   Create a new branch for your feature or bug fix.
    *   Write clean, well-commented, and typed Python code.
    *   Add tests for any new functionality or bug fixes. Ensure existing tests pass.
    *   Run linters and formatters: `black .`, `isort .`, `flake8 .`, `mypy src`. Using `pre-commit install` is highly recommended to automate this.
    *   Submit a Pull Request (PR) to the `main` branch. Clearly describe the changes made and the problem solved.

3.  **Problematic Plugins:**
    *   If you find a plugin that causes Pedalboard Pluginary or Pedalboard to crash or hang, please report it.
    *   You can also contribute to the `src/pedalboard_pluginary/resources/default_ignores.json` file by submitting a PR. The key for a plugin is typically its type (e.g., `aufx` or `vst3`) followed by its filename stem (e.g., `"vst3/RX 10 Connect"`).

4.  **Development Setup:**
    *   It's recommended to use a virtual environment.
    *   Install dependencies: `python3 -m pip install -e .[dev]`
    *   The project is built using `hatchling` (configured in `pyproject.toml`). A `build.sh` script is provided for convenience.

### Testing

*   Tests are written using `pytest` and are located in the `tests/` directory.
*   Code coverage is measured using `pytest-cov`.
*   To run tests:
    ```bash
    pytest
    ```
*   Continuous Integration (CI) is set up using GitHub Actions (see `.github/workflows/ci.yml`). Tests are run automatically on pushes and pull requests across multiple Python versions (3.9, 3.10, 3.11).

## Changelog Highlights

*(Based on `CHANGELOG.md` - For a full list of changes, please refer to the [CHANGELOG.md](CHANGELOG.md) file.)*

*   **January 2025 (Ongoing Development):**
    *   **Code Streamlining & Optimization:** Major initiative for code organization, performance tuning (SQLite, async), and cleanup.
    *   **`from __future__ import annotations`:** Applied across codebase.
    *   **SQLite Performance:** Further pragmas and optimizations.
    *   **Type Safety & Cleanup:** Continuous improvements, removal of dead code.
*   **December 2024 (Major Enhancements):**
    *   **SQLite Cache Backend:** Introduced high-performance SQLite cache with FTS, replacing JSON as default. Includes auto-migration.
    *   **Async Scanning Engine:** Implemented fully asynchronous plugin scanning for massive speed improvements.
    *   **Architectural Refactor:** Modularized scanner architecture, improved type safety with protocols and TypedDicts, unified serialization, custom exception hierarchy, progress reporting, retry logic, and timeout protection.
    *   **Pedalboard Type Stubs:** Created comprehensive stubs for improved static analysis.
    *   Achieved 100% mypy compliance in strict mode.
*   **v1.1.0 (Previous Release):**
    *   Added `update` CLI command (basic version).
    *   Added `json` and `yaml` output for `list` command.
*   **v1.0.0 (Initial Release):**
    *   Basic VST3 and AU scanning and listing.
    *   Initial command-line interface.
    *   JSON cache for plugin information.

## License

This project is licensed under the Apache License, Version 2.0. See the [LICENSE.txt](LICENSE.txt) file for details.

Copyright (c) 2023-2024 Adam Twardoch.

_Pedalboard Pluginary_ is not affiliated with [Pedalboard](https://github.com/spotify/pedalboard) or Spotify.

## Authors

*   Adam Twardoch ([@twardoch](https://github.com/twardoch))

(With assistance from AI tools for development and documentation.)
