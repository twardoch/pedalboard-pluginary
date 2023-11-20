# Pedalboard Pluginary

_Pedalboard Pluginary_ is an independent Python-based package and command-line tool that scans and lists VST-3 plugins on macOS and Windows, and Audio Unit (AU) plugins on macOS. It’s intended as a companion for the _[Pedalboard](https://github.com/spotify/pedalboard)_ Python library by Spotify, but it’s not affiliated with _Pedalboard_ or Spotify.

## Features

With _Pedalboard Pluginary_, you can scan and list VST-3 and AU audio plugins installed on your machine, including their default parameters. 

- It automatically scans and catalogs VST-3 and AU plugins installed on your system.
- Provides a command-line interface (CLI) for quick access to your plugin library.
- Saves the plugin information in a JSON file. This file has the information about the plugin parameters and their default values. 
- Works on Windows and macOS (Windows is currently untested).
- It bundles an `ignores.json` file, which “blacklists” some plugins that are known to cause issues with Pedalboard. It will not scan these, and will not include them in the cache. If you find that some plugins are not working with Pedalboard, you can add them to your `ignores.json` file. See “Contributing” section below.

## Future plans

I plan to extend the package with another functionality, “jobs”, which will allow to load a stack of plugins with their parameter values from a dictionary or JSON file, and run them in a batch using Pedalboard. 

## Installation

To install _Pedalboard Pluginary_, run:

```bash
python3 -m pip install --upgrade pedalboard-pluginary
```

For the current development version:

```bash
python3 -m pip install --upgrade git+https://github.com/twardoch/pedalboard-pluginary
```

## Command-line usage

After installation, you can use `pbpluginary` from the command line.

### Commands:

- `pbpluginary list` displays the plugin information stored in the cache, as a JSON. If no cache exists, it will scan your system and create the cache.
- `pbpluginary scan` scans all available plugins, and caches the information. Run this if you’ve installed or upgraded some VST-3 or AU plugins.

## Python usage

You can use _Pedalboard Pluginary_ as a library in your Python scripts. Here's a quick example:

```python
from pedalboard_pluginary import PedalboardPluginary

pluginary = PedalboardPluginary()
print(pluginary.list_plugins())
```

This snippet will list all plugins that have been scanned and cached, as a JSON.

## Changes

- **v1.1.0**: Added `update` CLI command which only scans plugins that aren’t cached yet. Not perfect. Added `json` and `yaml` CLI commands. Additional refactorings. 
- **v1.0.0**: Initial release with basic scanning and listing of both VST-3 and AU plugins, and command-line interface for easy interaction.

## License

- **Pedalboard Pluginary** is written by Adam Twardoch, with assistance from GPT-4.
- Copyright (c) 2023 Adam Twardoch.
- Licensed under the [Apache-2.0 license](https://raw.githubusercontent.com/twardoch/pedalboard-pluginary/main/LICENSE.txt).
- _Pedalboard Pluginary_ is not affiliated with [Pedalboard](https://github.com/spotify/pedalboard) or Spotify.

## Contributing

- If you encounter any issues or have suggestions, feel free to open an [issue](https://github.com/twardoch/pedalboard-pluginary/issues) on GitHub. 
- If you find that some plugins are not working with Pedalboard, open an issue that lists the key, which is the plugin type and the base filename, like `"aufx/CoreAudio"` or `"vst3/RX 10 Connect"`. You can also modify the [`default_ignores.json`](https://raw.githubusercontent.com/twardoch/pedalboard-pluginary/main/src/pedalboard_pluginary/resources/default_ignores.json) file, and submit a pull request.
- If you want to contribute code, please open a pull request. 
