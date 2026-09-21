import subprocess
import sys
import unittest


class LegacyPluginCompatibilityTests(unittest.TestCase):
    def test_core_imports_without_pathlib(self):
        script = r'''
import builtins
import sys

real_import = builtins.__import__

def blocked_import(name, *args, **kwargs):
    if name == "pathlib":
        raise ImportError("pathlib is unavailable in Sublime's legacy plugin host")
    return real_import(name, *args, **kwargs)

builtins.__import__ = blocked_import
sys.path.insert(0, "CompetitiveHelper")
import competitive_helper_core
assert competitive_helper_core.slugify("A/B") == "A_B"
'''
        result = subprocess.run([sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))

    def test_runner_module_can_be_loaded_by_legacy_plugin_host(self):
        script = r'''
import builtins
import sys

real_import = builtins.__import__

def blocked_import(name, *args, **kwargs):
    if name == "pathlib":
        raise ImportError("pathlib is unavailable in Sublime's legacy plugin host")
    return real_import(name, *args, **kwargs)

builtins.__import__ = blocked_import
sys.path.insert(0, "CompetitiveHelper")
import cph_runner
assert cph_runner.Path is None
'''
        result = subprocess.run([sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))


if __name__ == "__main__":
    unittest.main()
