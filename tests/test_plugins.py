import unittest
from pathlib import Path
from types import SimpleNamespace

from openrouter_agent.plugins import PluginManager


class PluginTests(unittest.TestCase):
    def test_load_manifest_registers_command(self):
        manager = PluginManager()
        manager.load_manifest(Path("plugins.json"))
        self.assertIn("/pluginping", manager.commands)
        self.assertEqual([], manager.errors)

    def test_run_dispatches_registered_command(self):
        manager = PluginManager()
        manager.load_manifest(Path("plugins.json"))
        handled, result = manager.run(
            "/pluginping hello",
            state=SimpleNamespace(active_project="P012"),
            runtime=SimpleNamespace(),
        )
        self.assertTrue(handled)
        self.assertIn("plugin-ping ok", result)
        self.assertIn("project=P012", result)
        self.assertIn("hello", result)


if __name__ == "__main__":
    unittest.main()
