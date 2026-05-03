import unittest
from types import SimpleNamespace
from unittest.mock import patch

from openrouter_agent.agents.core import AgentRuntime


class RuntimeReviewTests(unittest.TestCase):
    def test_print_review_handles_structured_issues(self):
        state = SimpleNamespace(verbose=1, dry_run=False, max_tool_iterations=25, auto_mode=False, smart_auto=False, review_enabled=False, auto_max_rounds=1)
        runtime = AgentRuntime(client=SimpleNamespace(chat=None), state=state)
        review = {
            "status": "needs_fix",
            "summary": "Needs work",
            "issues": [{"file": "app.py", "message": "bad"}],
        }

        with patch("openrouter_agent.agents.core.ui.table") as mock_table:
            runtime.print_review(review)

        mock_table.assert_called_once()
        table_args = mock_table.call_args[0]
        self.assertEqual("Reviewer Report", table_args[0])
        issues_row = table_args[1][2]
        self.assertIn('"file": "app.py"', issues_row[1])
        self.assertIn('"message": "bad"', issues_row[1])

    def test_run_task_performs_review_fix_round_when_needed(self):
        state = SimpleNamespace(
            verbose=0,
            dry_run=False,
            max_tool_iterations=25,
            auto_mode=True,
            smart_auto=False,
            review_enabled=True,
            auto_max_rounds=1,
            active_project="alpha",
        )
        runtime = AgentRuntime(client=SimpleNamespace(chat=None), state=state)
        with patch("openrouter_agent.agents.core.get_plugin_manager") as mock_plugins, patch(
            "openrouter_agent.agents.core.new_task_id", return_value="t1"
        ), patch("openrouter_agent.agents.core.log_task_start"), patch(
            "openrouter_agent.agents.core.log_task_plan"
        ), patch("openrouter_agent.agents.core.log_task_end"), patch(
            "openrouter_agent.agents.core.save_checkpoint"
        ), patch.object(runtime, "create_plan", side_effect=[{"steps": [{"id": 1}], "risk_level": "high"}, {"steps": [{"id": 1}], "risk_level": "high"}]) as mock_plan, patch.object(
            runtime, "execute_plan", side_effect=["first", "fixed"]
        ) as mock_exec, patch.object(runtime, "reviewer", return_value={"status": "needs_fix", "recommended_next_prompt": "fix this"}), patch.object(
            runtime, "fixer", return_value={"fix_goal": "apply", "user_prompt": "fix this"}
        ), patch.object(runtime, "print_plan"), patch.object(runtime, "print_review"), patch(
            "openrouter_agent.agents.core.remember"
        ):
            mock_plugins.return_value.emit_hook.side_effect = [
                {"blocked": False, "updates": {}, "warnings": []},
                {"blocked": False, "updates": {}, "warnings": []},
            ]
            result = runtime.run_task("do work")
        self.assertEqual("fixed", result)
        self.assertEqual(2, mock_plan.call_count)
        self.assertEqual(2, mock_exec.call_count)


if __name__ == "__main__":
    unittest.main()
