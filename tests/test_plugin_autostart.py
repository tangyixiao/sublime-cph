import importlib.util
import json
import sys
import tempfile
import types
import unittest
import urllib.request
from pathlib import Path


class PluginAutostartTests(unittest.TestCase):
    def test_plugin_loaded_starts_listener_without_command_palette(self):
        root = Path(tempfile.mkdtemp(prefix="sublime-cph-plugin-"))
        settings = {
            "port": 10046,
            "code_root": str(root),
            "template_path": str(root / "template.cpp"),
            "open_source": False,
            "auto_start": True,
        }
        sublime = types.ModuleType("sublime")
        sublime.load_settings = lambda name: types.SimpleNamespace(
            get=lambda key, default=None: settings.get(key, default)
        )
        sublime.set_timeout = lambda function, delay: function()
        sublime.active_window = lambda: types.SimpleNamespace(open_file=lambda path: None)
        sublime.error_message = lambda message: (_ for _ in ()).throw(RuntimeError(message))
        sublime_plugin = types.ModuleType("sublime_plugin")
        sublime_plugin.ApplicationCommand = object
        sublime_plugin.TextCommand = object
        old_sublime = sys.modules.get("sublime")
        old_sublime_plugin = sys.modules.get("sublime_plugin")
        sys.modules["sublime"] = sublime
        sys.modules["sublime_plugin"] = sublime_plugin
        sys.path.insert(0, str(Path("CompetitiveHelper").resolve()))
        try:
            spec = importlib.util.spec_from_file_location(
                "competitive_helper_autostart", "CompetitiveHelper/competitive_helper.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.plugin_loaded()
            payload = json.loads(urllib.request.urlopen("http://127.0.0.1:10046/health").read())
            self.assertTrue(payload["ok"])
            module.StopCphListenerCommand().run()
        finally:
            if old_sublime is None:
                sys.modules.pop("sublime", None)
            else:
                sys.modules["sublime"] = old_sublime
            if old_sublime_plugin is None:
                sys.modules.pop("sublime_plugin", None)
            else:
                sys.modules["sublime_plugin"] = old_sublime_plugin


if __name__ == "__main__":
    unittest.main()
