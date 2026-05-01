import json
import unittest
from pathlib import Path
from unittest.mock import patch

from openrouter_agent.state import AgentState


class StateSessionTests(unittest.TestCase):
    def test_save_project_session_writes_expected_fields(self):
        state = AgentState()
        state.routes = ["huggingface::model-a"]
        state.provider_mode = "huggingface"
        state.auto_mode = False
        state.smart_auto = False
        state.review_enabled = False
        state.auto_max_rounds = 7
        state.max_tool_iterations = 99
        state.temperature = 0.4
        state.verbose = 3
        state.dry_run = True
        state.command_history = ["/models", "/provider huggingface"]

        session_path = Path(r"C:\isolated\alpha\.agent_session.json")
        writes = {}

        def fake_write_text(self, text, encoding="utf-8"):
            writes["path"] = self
            writes["text"] = text
            return len(text)

        with patch("openrouter_agent.state.project_session_file", return_value=session_path), patch(
            "pathlib.Path.write_text", autospec=True, side_effect=fake_write_text
        ):
            state.save_project_session()

        self.assertEqual(session_path, writes["path"])
        payload = json.loads(writes["text"])
        self.assertEqual(["huggingface::model-a"], payload["routes"])
        self.assertEqual("huggingface", payload["provider_mode"])
        self.assertEqual(99, payload["max_tool_iterations"])
        self.assertTrue(payload["dry_run"])
        self.assertEqual(["/models", "/provider huggingface"], payload["command_history"])

    def test_load_project_session_restores_settings(self):
        session_path = Path(r"C:\isolated\alpha\.agent_session.json")
        payload = {
            "routes": ["openrouter::model-b"],
            "provider_mode": "openrouter",
            "auto_mode": False,
            "smart_auto": False,
            "review_enabled": False,
            "auto_max_rounds": 5,
            "max_tool_iterations": 33,
            "temperature": 0.6,
            "verbose": 2,
            "dry_run": True,
            "command_history": ["/models", "/discover"],
        }

        def fake_exists(self):
            return self == session_path

        def fake_read_text(self, encoding="utf-8"):
            if self == session_path:
                return json.dumps(payload)
            raise FileNotFoundError(self)

        state = AgentState()
        with patch("openrouter_agent.state.project_session_file", return_value=session_path), patch(
            "pathlib.Path.exists", autospec=True, side_effect=fake_exists
        ), patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            loaded = state.load_project_session()

        self.assertTrue(loaded)
        self.assertEqual(["openrouter::model-b"], state.routes)
        self.assertEqual("openrouter", state.provider_mode)
        self.assertFalse(state.auto_mode)
        self.assertFalse(state.smart_auto)
        self.assertFalse(state.review_enabled)
        self.assertEqual(5, state.auto_max_rounds)
        self.assertEqual(33, state.max_tool_iterations)
        self.assertEqual(0.6, state.temperature)
        self.assertEqual(2, state.verbose)
        self.assertTrue(state.dry_run)
        self.assertEqual(["/models", "/discover"], state.command_history)

    def test_record_command_keeps_only_last_fifty_entries(self):
        state = AgentState()
        for i in range(60):
            state.record_command(f"/cmd {i}")
        self.assertEqual(50, len(state.command_history))
        self.assertEqual("/cmd 10", state.command_history[0])
        self.assertEqual("/cmd 59", state.command_history[-1])


if __name__ == "__main__":
    unittest.main()
