---
title: CLI reference
layout: default
nav_order: 2
---

# CLI reference

Invoke the tool as `pbpluginary` or `python -m pedalboard_pluginary`. Every command accepts `--help`. Put `--verbose` before the command for debug logging: `pbpluginary --verbose scan`.

## scan

Discover plugins and write them to the cache.

```bash
pbpluginary scan
pbpluginary scan --rescan                 # clear the cache and scan everything
pbpluginary scan --extra-folders ~/Plugins
pbpluginary scan --workers 4 --timeout 60
```

| Option | Default | Meaning |
|--------|---------|---------|
| `--rescan` | off | Clear the cache first, then scan all plugins. |
| `--extra-folders PATH` | — | Extra folder(s) to scan; repeatable. |
| `--workers N` | CPU count (max 8) | Parallel scan workers. |
| `--timeout N` | 30 | Seconds to wait for a single plugin before skipping it. |

Each plugin loads in a separate subprocess. A plugin that hangs or crashes is recorded in the journal and skipped; the scan keeps going and can be resumed.

## list

Show the cached catalogue, optionally filtered.

```bash
pbpluginary list
pbpluginary list --type vst3
pbpluginary list --name reverb --vendor fabfilter
pbpluginary list --format json
```

| Option | Meaning |
|--------|---------|
| `--name TEXT` | Keep plugins whose name contains TEXT (case-insensitive). |
| `--vendor TEXT` | Keep plugins whose vendor/manufacturer contains TEXT. |
| `--type TEXT` | Keep only `vst3` or `aufx`. |
| `--format {table,json,yaml}` | Output format (default `table`). |

## json / yaml

Export the whole catalogue.

```bash
pbpluginary json -o plugins.json --pretty
pbpluginary yaml -o plugins.yaml
```

`json` keys the export by plugin id; `yaml` emits a list. Both write to stdout when `-o/--output` is omitted. YAML export needs PyYAML (installed by default).

## info

Print statistics — total plugins, counts per type, top vendors, and cache paths. If a scan journal is left behind, `info` flags it so you know a `scan` will resume.

## clear

Wipe the plugin cache. Prompts for confirmation first.
