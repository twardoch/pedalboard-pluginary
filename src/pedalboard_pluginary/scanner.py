import re
import os
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
from .utils import ensure_folder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Scanner")


class PedalboardScanner:
    def __init__(self):
        self.plugins_path = get_cache_path("plugins")
        self.plugins = {}

    def _from_pb_param(self, data):
        drep = str(data)
        try:
            return float(drep)
        except ValueError:
            pass
        if drep.lower() in ["true", "false"]:
            return drep.lower() == "true"
        return drep

    def _run_auval(self):
        try:
            process = subprocess.Popen(
                ["auval", "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                yield line
        except Exception as e:
            logger.error(f"Error running auval: {e}")

    def _find_au_plugins(self, plugin_type="aufx"):
        au_plugins = []
        regex = re.compile(r"aufx\s+(\w+)\s+(\w+)\s+-\s+(.*?):\s+(.*?)\s+\((.*?)\)")
        for line in self._run_auval():
            match = regex.match(line)
            if match:
                (
                    plugin_code,
                    vendor_code,
                    vendor_name,
                    plugin_name,
                    plugin_url,
                ) = match.groups()
                plugin_path = Path(unquote(urlparse(plugin_url).path))
                plugin_fn = plugin_path.stem
                plugin_key = f"{plugin_type}/{plugin_fn}"
                au_plugins.append(
                    (
                        plugin_key,
                        plugin_path,
                        plugin_fn,
                        vendor_name,
                        plugin_code,
                        vendor_code,
                    )
                )
        return au_plugins

    def _scan_au_plugins(self):
        plugin_type = "aufx"
        found_au_plugins = list(self._find_au_plugins(plugin_type))
        with tqdm(found_au_plugins, desc="Scanning AU", unit="") as pbar:
            for (
                plugin_key,
                plugin_path,
                plugin_fn,
                vendor_name,
                plugin_code,
                vendor_code,
            ) in pbar:
                if plugin_key in self.ignores:
                    continue
                pbar.set_description(f"{plugin_key}")
                plugin_path = str(plugin_path)
                plugin_names = pedalboard.AudioUnitPlugin.get_plugin_names_for_file(
                    plugin_path
                )
                for plugin_name in plugin_names:
                    if plugin_name in self.plugins:
                        continue
                    plugin = pedalboard.load_plugin(
                        plugin_path, plugin_name=plugin_name
                    )
                    plugin_params = {
                        k: self._from_pb_param(plugin.__getattr__(k))
                        for k in plugin.parameters.keys()
                    }
                    plugin_entry = {
                        "name": plugin_name,
                        "path": plugin_path,
                        "filename": plugin_fn,
                        "type": plugin_type,
                        "params": plugin_params,
                        "vendor_name": vendor_name,
                        "plugin_code": plugin_code,
                        "vendor_code": vendor_code,
                    }
                    self.plugins[plugin_name] = plugin_entry
                    self._save_plugins()

    def _find_vst_plugins(self, plugin_type="vst3"):
        vst_plugins = []
        folders = [
            Path("~/Library/Audio/Plug-Ins/VST3").expanduser(),
            Path("/Library/Audio/Plug-Ins/VST3"),
        ]

        if os.name == "nt":
            folders.extend(
                [
                    Path(os.getenv("ProgramFiles") + r"\Common Files\VST3"),
                    Path(os.getenv("ProgramFiles(x86)") + r"\Common Files\VST3"),
                ]
            )

        plugin_paths = list(
            itertools.chain.from_iterable(
                folder.glob(f"*.{plugin_type}") for folder in folders if folder.exists()
            )
        )
        for plugin_path in plugin_paths:
            plugin_fn = plugin_path.stem
            plugin_key = f"{plugin_type}/{plugin_fn}"
            vst_plugins.append((plugin_key, plugin_path, plugin_fn))
        return vst_plugins

    def _scan_vst_plugins(self):
        plugin_type = "vst3"
        found_vst_plugins = list(self._find_vst_plugins(plugin_type))
        with tqdm(found_vst_plugins, desc="Scanning VST", unit="") as pbar:
            for plugin_key, plugin_path, plugin_fn in pbar:
                if plugin_key in self.ignores:
                    continue
                pbar.set_description(f"{plugin_key}")
                plugin_path = str(plugin_path)
                plugin_names = pedalboard.VST3Plugin.get_plugin_names_for_file(
                    plugin_path
                )
                for plugin_name in plugin_names:
                    if plugin_name in self.plugins:
                        continue
                    plugin = pedalboard.load_plugin(
                        plugin_path, plugin_name=plugin_name
                    )
                    plugin_params = {
                        k: self._from_pb_param(plugin.__getattr__(k))
                        for k in plugin.parameters.keys()
                    }
                    plugin_entry = {
                        "name": plugin_name,
                        "path": plugin_path,
                        "filename": plugin_fn,
                        "type": plugin_type,
                        "params": plugin_params,
                    }
                    self.plugins[plugin_name] = plugin_entry
                    self._save_plugins()

    def _ensure_ignores(self):
        self.ignores_path = get_cache_path("ignores")
        if not self.ignores_path.exists():
            copy_default_ignores(self.ignores_path)
        self.ignores = load_ignores(self.ignores_path)

    def _save_plugins(self):
        ensure_folder(self.plugins_path)
        save_json_file(dict(sorted(self.plugins.items())), self.plugins_path)

    def scan(self):
        logger.info("\n>> Scanning plugins...")
        self._ensure_ignores()
        self._scan_vst_plugins()
        self._scan_au_plugins()
        self._save_plugins()
        logger.info("\n>> Done!")

    def get_json(self):
        return json.dumps(self.plugins, indent=4)
