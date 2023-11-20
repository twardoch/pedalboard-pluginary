import re
import os
import platform
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse
import itertools
import logging
import pedalboard
from tqdm import tqdm
from .data import (
    load_json_file,
    save_json_file,
    get_cache_path,
    load_ignores,
    copy_default_ignores,
)
from .utils import ensure_folder, from_pb_param

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Scanner")


class PedalboardScanner:
    RE_AUFX = re.compile(r"aufx\s+(\w+)\s+(\w+)\s+-\s+(.*?):\s+(.*?)\s+\((.*?)\)")

    def __init__(self):
        self.plugins_path = get_cache_path("plugins")
        self.plugins = {}
        self.safe_save = True
        self.ensure_ignores()

    def ensure_ignores(self):
        self.ignores_path = get_cache_path("ignores")
        if not self.ignores_path.exists():
            copy_default_ignores(self.ignores_path)
        self.ignores = load_ignores(self.ignores_path)

    def save_plugins(self):
        ensure_folder(self.plugins_path)
        save_json_file(dict(sorted(self.plugins.items())), self.plugins_path)

    def _list_aufx_plugins(self):
        try:
            result = subprocess.run(
                ["auval", "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=True,
            )
            return result.stdout.splitlines()
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running auval: {e}")
            return []

    def _find_aufx_plugins(self, plugin_paths=None):
        if plugin_paths:
            plugin_paths = [Path(p).resolve() for p in plugin_paths]
        aufx_plugins = []
        plugin_type = "aufx"
        for line in self._list_aufx_plugins():
            match = self.RE_AUFX.match(line)
            if match:
                (
                    plugin_code,
                    vendor_code,
                    vendor_name,
                    plugin_name,
                    plugin_url,
                ) = match.groups()
                plugin_path = Path(unquote(urlparse(plugin_url).path)).resolve()
                plugin_fn = plugin_path.stem
                plugin_key = f"{plugin_type}/{plugin_fn}"
                if plugin_key not in self.ignores:
                    if plugin_paths and plugin_path not in plugin_paths:
                        continue
                    aufx_plugins.append(plugin_path)
        return aufx_plugins

    def _get_vst3_folders(self, extra_folders=None):
        os_name = platform.system()

        if os_name == "Windows":
            folders = [
                Path(os.getenv("ProgramFiles", "") + r"\Common Files\VST3"),
                Path(os.getenv("ProgramFiles(x86)", "") + r"\Common Files\VST3"),
            ]
        elif os_name == "Darwin":  # macOS
            folders = [
                Path("~/Library/Audio/Plug-Ins/VST3").expanduser(),
                Path("/Library/Audio/Plug-Ins/VST3"),
            ]
        elif os_name == "Linux":
            folders = [
                Path("~/.vst3").expanduser(),
                Path("/usr/lib/vst3"),
                Path("/usr/local/lib/vst3"),
            ]
        else:
            folders = []

        if extra_folders:
            folders.extend(Path(p) for p in extra_folders)

        return [folder for folder in folders if folder.exists()]

    def _find_vst3_plugins(self, extra_folders=None, plugin_paths=None):
        vst3_plugins = []
        plugin_type = "vst3"
        if plugin_paths:
            plugin_paths = [Path(p).resolve() for p in plugin_paths]

        plugin_paths = plugin_paths or list(
            itertools.chain.from_iterable(
                folder.glob(f"*.{plugin_type}")
                for folder in self._get_vst3_folders(extra_folders=extra_folders)
            )
        )
        for plugin_path in plugin_paths:
            plugin_fn = plugin_path.stem
            plugin_key = f"{plugin_type}/{plugin_fn}"
            if plugin_key not in self.ignores:
                vst3_plugins.append(plugin_path)
        return vst3_plugins

    def get_plugin_params(self, plugin_path, plugin_name):
        plugin = pedalboard.load_plugin(str(plugin_path), plugin_name=plugin_name)
        plugin_params = {
            k: from_pb_param(plugin.__getattr__(k)) for k in plugin.parameters.keys()
        }
        return plugin_params

    def scan_typed_plugin_path(
        self, plugin_type, plugin_key, plugin_path, plugin_fn, plugin_loader
    ):
        plugin_path = str(plugin_path)
        plugin_names = plugin_loader.get_plugin_names_for_file(plugin_path)
        for plugin_name in plugin_names:
            if plugin_name in self.plugins:
                continue
            plugin_params = self.get_plugin_params(plugin_path, plugin_name)
            plugin_entry = {
                "name": plugin_name,
                "path": plugin_path,
                "filename": plugin_fn,
                "type": plugin_type,
                "params": plugin_params,
            }
            self.plugins[plugin_name] = plugin_entry

    def scan_typed_plugins(self, plugin_type, found_plugins, plugin_loader):
        with tqdm(found_plugins, desc=f"Scanning {plugin_type}", unit="") as pbar:
            for plugin_path in pbar:
                plugin_fn = str(Path(plugin_path).stem)
                plugin_key = f"{plugin_type}/{plugin_fn}"
                pbar.set_description(plugin_key)
                self.scan_typed_plugin_path(
                    plugin_type, plugin_key, str(plugin_path), plugin_fn, plugin_loader
                )
                if self.safe_save:
                    self.save_plugins()

    def scan_aufx_plugins(self, plugin_paths=None):
        self.scan_typed_plugins(
            "aufx",
            list(self._find_aufx_plugins(plugin_paths=plugin_paths)),
            pedalboard.AudioUnitPlugin,
        )

    def scan_vst3_plugins(self, extra_folders=None, plugin_paths=None):
        self.scan_typed_plugins(
            "vst3",
            list(
                self._find_vst3_plugins(
                    extra_folders=extra_folders, plugin_paths=plugin_paths
                )
            ),
            pedalboard.VST3Plugin,
        )

    def scan_plugins(self, extra_folders=None, plugin_paths=None):
        self.scan_vst3_plugins(extra_folders=extra_folders, plugin_paths=plugin_paths)
        if platform.system() == "Darwin":
            self.scan_aufx_plugins(plugin_paths=plugin_paths)

    def scan(self, extra_folders=None, plugin_paths=None):
        logger.info("\n>> Scanning plugins...")
        self.scan_plugins(extra_folders=None, plugin_paths=plugin_paths)
        self.save_plugins()
        logger.info("\n>> Done!")

    def rescan(self, extra_folders=None): 
        self.plugins = {}
        self.scan(extra_folders=extra_folders)        

    def update(self, extra_folders=None):
        logger.info("\n>> Scanning updated plugins...")
        if not self.plugins_path.exists():
            self.rescan(extra_folders=extra_folders)
            return
        self.plugins = load_json_file(self.plugins_path)
        new_vst3_paths = sorted(list(set(self._find_vst3_plugins(extra_folders=extra_folders)) - set(Path(p["path"]).resolve() for p in self.plugins.values() if p["type"] == "vst3")))
        self.scan_vst3_plugins(extra_folders=extra_folders, plugin_paths=new_vst3_paths)
        new_aufx_paths = sorted(list(set(self._find_aufx_plugins()) - set(Path(p["path"]).resolve() for p in self.plugins.values() if p["type"] == "aufx")))
        if platform.system() == "Darwin":
            self.scan_aufx_plugins(plugin_paths=new_aufx_paths)
        self.save_plugins()
        logger.info("\n>> Done!")

    def get_json(self):
        return json.dumps(self.plugins, indent=4)
