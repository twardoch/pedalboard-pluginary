# Pedalboard Pluginary

[![PyPI version](https://badge.fury.io/py/pedalboard-pluginary.svg)](https://pypi.org/project/pedalboard-pluginary/)
[![Python versions](https://img.shields.io/pypi/pyversions/pedalboard-pluginary.svg)](https://pypi.org/project/pedalboard-pluginary/)
[![CI](https://github.com/twardoch/pedalboard-pluginary/actions/workflows/ci.yml/badge.svg)](https://github.com/twardoch/pedalboard-pluginary/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Find every VST3 and Audio Unit plugin on your machine, read its parameters, and query the lot from Python or the shell. Pedalboard Pluginary scans each plugin in its own subprocess, so the one plugin that segfaults on load can't take the whole scan down with it.

It is a companion to Spotify's [Pedalboard](https://github.com/spotify/pedalboard) library, which it uses to introspect plugins. It is not affiliated with Spotify.

## Quick start

```bash
pip install pedalboard-pluginary

pbpluginary scan          # discover and catalogue your plugins
pbpluginary list          # show them in a table
pbpluginary info          # counts, top vendors, cache location
```

The first scan can take a while; results are cached in a local SQLite database, so every command after that is instant. If a scan is interrupted, the next `scan` resumes where it stopped.

## Why it exists

`pedalboard.load_plugin()` needs an exact path and name. Getting those for a whole plugin collection means walking several platform-specific folders, parsing `auval` output on macOS, and surviving plugins that crash on load. Pedalboard Pluginary does that once and hands you a clean, queryable catalogue.

## Command-line usage

### Scan

```bash
pbpluginary scan                          # incremental: skip already-cached plugins
pbpluginary scan --rescan                 # clear cache and scan everything
pbpluginary scan --extra-folders ~/Plugins
pbpluginary scan --workers 4 --timeout 60
```

Each plugin is loaded in a separate subprocess with a timeout. A plugin that hangs or crashes is recorded and skipped; the scan keeps going.

### List and search

```bash
pbpluginary list                          # all plugins, as a table
pbpluginary list --type vst3              # only VST3 (or: aufx)
pbpluginary list --name reverb            # name contains "reverb"
pbpluginary list --vendor fabfilter       # vendor contains "fabfilter"
pbpluginary list --format json            # table | json | yaml
```

### Export and manage

```bash
pbpluginary json -o plugins.json --pretty
pbpluginary yaml -o plugins.yaml
pbpluginary info                          # statistics and cache paths
pbpluginary clear                         # wipe the cache (asks first)
```

Add `--verbose` before any command for debug logging: `pbpluginary --verbose scan`.

## Python usage

```python
from pedalboard_pluginary import PedalboardPluginary

pp = PedalboardPluginary()

# Scan (writes to the SQLite cache). Optional: rescan=True, extra_folders=[...]
pp.scan()

# Query the cache — returns a list of dicts
for plugin in pp.list_plugins(type="vst3"):
    print(plugin["name"], plugin["manufacturer"], plugin["path"])

# Look up one plugin by its id, e.g. "vst3/FabFilter Pro-Q 3"
details = pp.get_plugin_details("vst3/FabFilter Pro-Q 3")
```

`list_plugins()` accepts `name`, `manufacturer`, and `type` filters. Each result carries `id`, `name`, `path`, `type`, `manufacturer`, and `params` (a name→value map).

## Platform support

| Format | macOS | Windows | Linux |
|--------|:-----:|:-------:|:-----:|
| VST3   | yes   | yes     | yes   |
| AU (aufx) | yes | —      | —     |

Audio Units exist only on macOS, so AU scanning runs there alone (via `auval`). VST3 discovery works everywhere Pedalboard runs. The cache lives under the platform's standard data directory: `~/Library/Application Support` on macOS, `%APPDATA%` on Windows, and `$XDG_CACHE_HOME` (or `~/.cache`) on Linux.

## How it works

- **Process isolation** — every plugin is scanned in a subprocess (`scan_single.py`). A crash there is caught and logged, never propagated.
- **Journaling** — a SQLite journal records progress per plugin, so an interrupted scan resumes instead of restarting.
- **SQLite storage** — plugins live in a SQLite database with an FTS5 index for fast search.
- **Parallelism** — a thread pool drives the subprocesses; tune it with `--workers`.

## Development

```bash
git clone https://github.com/twardoch/pedalboard-pluginary
cd pedalboard-pluginary
uvx hatch test          # run the test suite (plugin scanning is fully mocked)
./build.sh              # lint, format-check, test, and build
```

Versioning is git-tag based via `hatch-vcs`. Lint and format with `ruff`, type-check with `mypy`.

## License

Apache-2.0. See [LICENSE.txt](LICENSE.txt). Copyright © 2023–2026 Adam Twardoch.
