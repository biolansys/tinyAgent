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


if __name__ == "__main__":
    unittest.main()
