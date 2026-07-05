---
title: Architecture
layout: default
nav_order: 3
---

# Architecture

Loading an audio plugin runs third-party native code inside your process. Some plugins crash, some hang, and either one can take down a naive scanner. Pedalboard Pluginary is built around that fact.

## Process isolation

Every plugin is loaded in a separate subprocess (`scan_single.py`), driven by a thread pool from the parent (`scanner_isolated.py`). A segfault or a C++ exception inside a plugin kills only its subprocess; the parent records the failure and moves on. This is why a thread pool — not `asyncio` — sits at the centre: threads exist to launch and supervise subprocesses, one per plugin.

## Journaling and resume

Before a scan starts, the discovered plugins are written to a SQLite journal as pending work. As each subprocess finishes, its entry flips to success or failure. If the whole run is interrupted, the next `scan` reads the journal and processes only what is still pending — you never re-scan a 500-plugin library from scratch because of one Ctrl-C. On a clean finish the journal is committed into the main cache and deleted.

## SQLite storage

Plugins live in a SQLite database with an FTS5 full-text index, so name and vendor searches stay fast even with tens of thousands of entries. The cache path follows each platform's convention:

- macOS — `~/Library/Application Support/com.twardoch.pedalboard-pluginary/`
- Windows — `%APPDATA%\com.twardoch.pedalboard-pluginary\`
- Linux — `$XDG_CACHE_HOME` (or `~/.cache`) `/com.twardoch.pedalboard-pluginary/`

## Ignoring problem plugins

A bundled `default_ignores.json` lists plugins known to crash or hang on load; discovery skips them. Add your own entries to `ignores.json` in the cache directory. The key is `<type>/<filename-stem>`, e.g. `vst3/RX 10 Connect`.

## Plugin discovery

VST3 files are found by globbing the standard plugin folders per platform. On macOS, Audio Units are discovered by parsing `auval -l` output and resolving each component's file URL. Everything then flows through the same isolated-scan pipeline.
