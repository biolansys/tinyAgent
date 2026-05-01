import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from openrouter_agent import cli


def make_state():
    return SimpleNamespace(
        active_project="alpha",
        routes=["openrouter::default"],
        provider_mode="auto",
        auto_mode=True,
        smart_auto=True,
        review_enabled=True,
        auto_max_rounds=3,
        max_tool_iterations=25,
        temperature=0.2,
        verbose=1,
        dry_run=False,
        command_history=[],
        usage={},
        load_project_session=MagicMock(),
        save_project_session=MagicMock(),
        record_command=MagicMock(),
    )


def make_runtime():
    return SimpleNamespace(client=object(), reset_messages=MagicMock(), run_task=MagicMock())


class ProjectCommandTests(unittest.TestCase):
    def test_projectinfo_shows_current_project(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.project_info_text", return_value="Name: alpha"), patch("builtins.print") as mock_print:
            handled = cli.handle_exact_command("/projectinfo", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("Name: alpha")

    def test_projectrename_updates_active_project(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.confirm_project_action", return_value=True), patch(
            "openrouter_agent.cli.rename_project", return_value="beta"
        ), patch("openrouter_agent.cli.MultiProviderClient", return_value="client"), patch(
            "openrouter_agent.cli.ui.success"
        ), patch("openrouter_agent.cli.ui.info"):
            handled = cli.handle_prefixed_command("/projectrename alpha beta", state, runtime)
        self.assertTrue(handled)
        self.assertEqual("beta", state.active_project)
        state.load_project_session.assert_called_once()
        state.save_project_session.assert_called_once()
        runtime.reset_messages.assert_called_once()

    def test_projectdelete_cancellation_skips_delete(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.confirm_project_action", return_value=False), patch(
            "openrouter_agent.cli.delete_project"
        ) as mock_delete, patch("openrouter_agent.cli.ui.warn"):
            handled = cli.handle_prefixed_command("/projectdelete alpha", state, runtime)
        self.assertTrue(handled)
        mock_delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
