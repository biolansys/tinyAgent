import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from openrouter_agent.plugins import PluginManager
from openrouter_agent.project_context import create_project, delete_project
from openrouter_agent.agents.core import AgentRuntime


class PluginHookTests(unittest.TestCase):
    def test_manifest_loads_recommended_hooks(self):
        manager = PluginManager()
        manager.load_manifest(Path("plugins.json"))
        self.assertIn("on_project_created", manager.hooks)
        self.assertIn("before_task", manager.hooks)
        self.assertIn("after_task", manager.hooks)

    def test_before_task_mutation_supported(self):
        manager = PluginManager()
        manager.load_manifest(Path("plugins.json"))
        result = manager.emit_hook("before_task", {"user_input": "!hello"})
        self.assertFalse(result["blocked"])
        self.assertEqual("hello", result["updates"].get("user_input"))

    def test_create_project_emits_on_project_created(self):
        name = f"plugintest-{uuid.uuid4().hex[:8]}"
        with patch("openrouter_agent.project_context.get_plugin_manager") as mock_get:
            mock_get.return_value.emit_hook.return_value = {"blocked": False, "updates": {}, "warnings": []}
            created = create_project(name)
        self.assertEqual(name, created)
        mock_get.return_value.emit_hook.assert_called_once()
        delete_project(name)

    def test_run_task_respects_before_task_block(self):
        runtime = AgentRuntime(
            client=SimpleNamespace(),
            state=SimpleNamespace(
                verbose=0,
                dry_run=False,
                retry_safe_mode=False,
                max_tool_iterations=1,
                review_enabled=False,
                auto_max_rounds=0,
                active_project="alpha",
            ),
        )
        with patch("openrouter_agent.agents.core.get_plugin_manager") as mock_plugins:
            mock_plugins.return_value.emit_hook.side_effect = [
                {"blocked": True, "reason": "policy", "updates": {}, "warnings": []}
            ]
            result = runtime.run_task("anything")
        self.assertIn("Task blocked by plugin hook: policy", result)


if __name__ == "__main__":
    unittest.main()
