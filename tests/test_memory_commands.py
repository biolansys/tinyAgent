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


class MemoryCommandTests(unittest.TestCase):
    def test_memory_command_prints_memory_json(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.load_memory", return_value={"notes": []}), patch("builtins.print") as mock_print:
            handled = cli.handle_exact_command("/memory", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once()

    def test_memorynote_command_saves_note(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.remember", return_value="Memory saved.") as mock_remember, patch("builtins.print") as mock_print:
            handled = cli.handle_prefixed_command("/memorynote remember this", state, runtime)
        self.assertTrue(handled)
        mock_remember.assert_called_once_with("remember this")
        mock_print.assert_called_once_with("Memory saved.")

    def test_projectclone_command_activates_cloned_project(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.clone_project", return_value="beta"), patch(
            "openrouter_agent.cli.current_project_root", return_value="C:/workspace/beta"
        ), patch("openrouter_agent.cli.MultiProviderClient", return_value="client"), patch(
            "openrouter_agent.cli.ui.success"
        ), patch("openrouter_agent.cli.ui.info"):
            handled = cli.handle_prefixed_command("/projectclone alpha beta", state, runtime)
        self.assertTrue(handled)
        self.assertEqual("beta", state.active_project)


if __name__ == "__main__":
    unittest.main()
