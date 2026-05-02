import unittest
from types import SimpleNamespace

from openrouter_agent.subagents import (
    SUBAGENT_ROLES,
    build_subagent_context,
    build_subagent_messages,
    normalize_subagent_context,
    run_subagent,
)


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def chat(self, messages, tools=None, force_no_tools=False):
        self.calls.append(
            {
                "messages": messages,
                "tools": tools,
                "force_no_tools": force_no_tools,
            }
        )
        if tools is not None:
            raise AssertionError("Subagents must not request tools")
        if not force_no_tools:
            raise AssertionError("Subagents must force tool-free execution")
        return self.response


class SubagentTests(unittest.TestCase):
    def test_normalize_subagent_context_serializes_objects(self):
        self.assertEqual(
            '{\n  "a": 1,\n  "b": 2\n}',
            normalize_subagent_context({"b": 2, "a": 1}),
        )

    def test_build_subagent_messages_includes_role_and_context(self):
        state = SimpleNamespace(active_project="demo", provider_mode="auto")
        messages = build_subagent_messages(state, "plan", "Outline the work", context={"step": 1})

        self.assertEqual(2, len(messages))
        self.assertEqual("system", messages[0]["role"])
        self.assertIn("read-only planning subagent", messages[0]["content"])
        self.assertEqual("user", messages[1]["role"])
        self.assertIn("Role: plan", messages[1]["content"])
        self.assertIn("Active project: demo", messages[1]["content"])
        self.assertIn("Role focus:", messages[1]["content"])
        self.assertIn('"step": 1', messages[1]["content"])

    def test_build_subagent_messages_for_worker_includes_target_file(self):
        state = SimpleNamespace(active_project="demo", provider_mode="auto")
        messages = build_subagent_messages(
            state,
            "worker",
            "Update the file",
            context={"target_file": "app.py", "ownership": "Only this file may change.", "current_content": "print(1)"},
        )

        self.assertEqual(2, len(messages))
        self.assertIn("write-capable worker subagent", messages[0]["content"])
        self.assertIn("Target file: app.py", messages[1]["content"])
        self.assertIn("Only this file may change.", messages[1]["content"])
        self.assertIn("Current file contents:", messages[1]["content"])

    def test_build_subagent_context_includes_latest_task_context(self):
        state = SimpleNamespace(active_project="demo", provider_mode="auto", routes=["demo::route"])
        with unittest.mock.patch("openrouter_agent.subagents.load_task_context", return_value={"task_id": "t1"}):
            context = build_subagent_context(state, "review")

        self.assertEqual("review", context["role"])
        self.assertEqual("demo", context["active_project"])
        self.assertEqual(["demo::route"], context["routes"])
        self.assertEqual({"task_id": "t1"}, context["task"])

    def test_run_subagent_rejects_unknown_role(self):
        client = FakeClient({"choices": [{"message": {"content": "unused"}}]})
        state = SimpleNamespace(active_project="demo", provider_mode="auto")

        with self.assertRaises(ValueError):
            run_subagent(client, state, "inspect", "Look around")

        self.assertEqual([], client.calls)

    def test_run_subagent_returns_normalized_shape_without_tools(self):
        response = {
            "_route": "openrouter::test-model",
            "_provider": "openrouter",
            "_model": "test-model",
            "_tools_enabled": False,
            "choices": [{"message": {"content": "plan result", "tool_calls": [{"id": "x"}]}}],
        }
        client = FakeClient(response)
        state = SimpleNamespace(active_project="demo", provider_mode="auto")

        result = run_subagent(client, state, "review", "Check this", context=["note"])

        self.assertEqual(1, len(client.calls))
        self.assertEqual("review", result["role"])
        self.assertEqual("Check this", result["prompt"])
        self.assertEqual('[\n  "note"\n]', result["context"])
        self.assertIsNone(result["task_context"])
        self.assertEqual("plan result", result["content"])
        self.assertEqual("openrouter::test-model", result["route"])
        self.assertFalse(result["tools_enabled"])
        self.assertEqual(2, len(result["messages"]))
        self.assertEqual("system", result["messages"][0]["role"])
        self.assertEqual("user", result["messages"][1]["role"])

    def test_allowed_roles_are_small_and_fixed(self):
        self.assertEqual(("plan", "review", "search", "worker"), SUBAGENT_ROLES)


if __name__ == "__main__":
    unittest.main()
