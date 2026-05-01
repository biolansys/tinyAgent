import unittest
from types import SimpleNamespace
from unittest.mock import patch

from openrouter_agent.agents.core import AgentRuntime


class RepeatingClient:
    def __init__(self):
        self.calls = 0

    def chat(self, _messages, tools=None, force_no_tools=False):
        self.calls += 1
        return {
            "_tools_enabled": True,
            "choices": [{
                "message": {
                    "content": "",
                    "tool_calls": [{
                        "id": "call-1",
                        "function": {"name": "read_text_file", "arguments": "{\"path\":\"README.md\"}"},
                    }],
                }
            }],
        }


class SequencedClient:
    def __init__(self):
        self.calls = 0

    def chat(self, _messages, tools=None, force_no_tools=False):
        self.calls += 1
        if self.calls == 1:
            return {
                "_tools_enabled": True,
                "choices": [{
                    "message": {
                        "content": "",
                        "tool_calls": [{
                            "id": "call-1",
                            "function": {"name": "read_text_file", "arguments": "{\"path\":\"README.md\"}"},
                        }],
                    }
                }],
            }
        return {
            "_tools_enabled": False,
            "choices": [{"message": {"content": "done"}}],
        }


def make_state():
    return SimpleNamespace(
        verbose=0,
        dry_run=False,
        retry_safe_mode=False,
        max_tool_iterations=10,
        auto_mode=False,
        smart_auto=False,
        review_enabled=False,
        auto_max_rounds=1,
    )


class RuntimeLoopGuardTests(unittest.TestCase):
    def test_execute_step_stops_on_repeated_tool_cycles(self):
        runtime = AgentRuntime(client=RepeatingClient(), state=make_state())
        with patch("openrouter_agent.agents.core.read_memory_text", return_value=""), patch(
            "openrouter_agent.agents.core.log_tool_call"
        ):
            result = runtime.execute_step("do work", {"steps": [{"id": 1}]}, {"id": 1, "title": "x"})
        self.assertIn("repeated tool-call cycles", result)
        self.assertIn("read_text_file", result)

    def test_execute_step_continues_when_cycle_changes_to_completion(self):
        runtime = AgentRuntime(client=SequencedClient(), state=make_state())
        with patch("openrouter_agent.agents.core.read_memory_text", return_value=""), patch(
            "openrouter_agent.agents.core.log_tool_call"
        ):
            result = runtime.execute_step("do work", {"steps": [{"id": 1}]}, {"id": 1, "title": "x"})
        self.assertEqual("done", result)

    def test_execute_step_safe_retry_blocks_mutating_tool_on_denied_confirmation(self):
        state = make_state()
        state.retry_safe_mode = True
        runtime = AgentRuntime(client=SequencedClient(), state=state)
        tool_called = {"value": False}

        def fake_write_text_file(**_kwargs):
            tool_called["value"] = True
            return "written"

        with patch("openrouter_agent.agents.core.read_memory_text", return_value=""), patch(
            "openrouter_agent.agents.core.log_tool_call"
        ), patch("builtins.input", return_value="n"), patch.dict(
            "openrouter_agent.agents.core.TOOLS", {"write_text_file": fake_write_text_file}, clear=False
        ), patch.object(
            runtime.client,
            "chat",
            side_effect=[
                {
                    "_tools_enabled": True,
                    "choices": [{
                        "message": {
                            "content": "",
                            "tool_calls": [{
                                "id": "call-1",
                                "function": {"name": "write_text_file", "arguments": "{\"path\":\"a.txt\",\"content\":\"x\"}"},
                            }],
                        }
                    }],
                },
                {"_tools_enabled": False, "choices": [{"message": {"content": "done"}}]},
            ],
        ):
            result = runtime.execute_step("do work", {"steps": [{"id": 1}]}, {"id": 1, "title": "x"})
        self.assertEqual("done", result)
        self.assertFalse(tool_called["value"])

    def test_execute_step_edit_scope_blocks_other_file_mutation(self):
        state = make_state()
        state.edit_target_file = "allowed.txt"
        runtime = AgentRuntime(client=SequencedClient(), state=state)
        tool_called = {"value": False}

        def fake_write_text_file(**_kwargs):
            tool_called["value"] = True
            return "written"

        with patch("openrouter_agent.agents.core.read_memory_text", return_value=""), patch(
            "openrouter_agent.agents.core.log_tool_call"
        ), patch.dict(
            "openrouter_agent.agents.core.TOOLS", {"write_text_file": fake_write_text_file}, clear=False
        ), patch.object(
            runtime.client,
            "chat",
            side_effect=[
                {
                    "_tools_enabled": True,
                    "choices": [{
                        "message": {
                            "content": "",
                            "tool_calls": [{
                                "id": "call-1",
                                "function": {"name": "write_text_file", "arguments": "{\"path\":\"other.txt\",\"content\":\"x\"}"},
                            }],
                        }
                    }],
                },
                {"_tools_enabled": False, "choices": [{"message": {"content": "done"}}]},
            ],
        ):
            result = runtime.execute_step("do work", {"steps": [{"id": 1}]}, {"id": 1, "title": "x"})
        self.assertEqual("done", result)
        self.assertFalse(tool_called["value"])
        self.assertEqual("allowed.txt", state.edit_target_file)


if __name__ == "__main__":
    unittest.main()
