import unittest
from types import SimpleNamespace
from unittest.mock import patch

from openrouter_agent.agents.core import AgentRuntime


class DoneClient:
    def chat(self, _messages, tools=None, force_no_tools=False):
        return {
            "_tools_enabled": False,
            "choices": [{"message": {"content": "done"}}],
        }


def make_state():
    return SimpleNamespace(
        verbose=0,
        dry_run=False,
        max_tool_iterations=5,
        auto_mode=False,
        smart_auto=False,
        review_enabled=False,
        auto_max_rounds=1,
    )


class RuntimeResumeTests(unittest.TestCase):
    def test_resume_task_runs_from_checkpoint(self):
        runtime = AgentRuntime(client=DoneClient(), state=make_state())
        checkpoint = {
            "task_id": "run123",
            "status": "in_progress",
            "user_input": "do x",
            "plan": {"steps": [{"id": 1, "title": "Do it"}]},
            "next_step_index": 0,
            "step_outputs": [],
        }
        with patch("openrouter_agent.agents.core.load_checkpoint", return_value=checkpoint), patch(
            "openrouter_agent.agents.core.save_checkpoint"
        ), patch("openrouter_agent.agents.core.log_task_end"), patch(
            "openrouter_agent.agents.core.read_memory_text", return_value=""
        ):
            result = runtime.resume_task("run123")
        self.assertIn("Step 1: done", result)


if __name__ == "__main__":
    unittest.main()
