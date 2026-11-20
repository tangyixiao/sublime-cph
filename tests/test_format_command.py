import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path


class _FakeRegion:
    def __init__(self, begin, end):
        self.begin = begin
        self.end = end


class _FakeView:
    def __init__(self, filename, content):
        self.filename = filename
        self.content = content

    def file_name(self):
        return str(self.filename)

    def size(self):
        return len(self.content)

    def substr(self, region):
        return self.content[region.begin : region.end]

    def replace(self, edit, region, content):
        self.content = content


def _load_plugin(settings):
    sublime = types.ModuleType("sublime")
    sublime.Region = _FakeRegion
    sublime.load_settings = lambda name: types.SimpleNamespace(
        get=lambda key, default=None: settings.get(key, default)
    )
    sublime.error_message = lambda message: (_ for _ in ()).throw(RuntimeError(message))
    sublime_plugin = types.ModuleType("sublime_plugin")
    sublime_plugin.ApplicationCommand = object
    class _TextCommand:
        def __init__(self, view):
            self.view = view

    sublime_plugin.TextCommand = _TextCommand
    old_sublime = sys.modules.get("sublime")
    old_sublime_plugin = sys.modules.get("sublime_plugin")
    sys.modules["sublime"] = sublime
    sys.modules["sublime_plugin"] = sublime_plugin
    sys.path.insert(0, str(Path("CompetitiveHelper").resolve()))
    spec = importlib.util.spec_from_file_location(
        "competitive_helper_format", "CompetitiveHelper/competitive_helper.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def restore():
        if old_sublime is None:
            sys.modules.pop("sublime", None)
        else:
            sys.modules["sublime"] = old_sublime
        if old_sublime_plugin is None:
            sys.modules.pop("sublime_plugin", None)
        else:
            sys.modules["sublime_plugin"] = old_sublime_plugin

    return module, restore


class FormatCommandTests(unittest.TestCase):
    def test_format_command_replaces_current_buffer_with_clang_format_output(self):
        with tempfile.TemporaryDirectory() as temp:
            filename = Path(temp) / "example.cpp"
            filename.write_text("int main(){return 0;}\n", encoding="utf-8")
            settings = {"clang_format_program": "clang-format"}
            module, restore = _load_plugin(settings)
            try:
                view = _FakeView(filename, filename.read_text(encoding="utf-8"))

                module.FormatCphFileCommand(view).run(None)

                self.assertEqual(view.content, "int main() { return 0; }\n")
            finally:
                restore()


if __name__ == "__main__":
    unittest.main()
