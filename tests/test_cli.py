import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from openrouter_agent import cli


def make_state():
    return SimpleNamespace(
        routes=["openrouter::default"],
        active_project="alpha",
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
        usage={"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "by_route": {}},
        load_project_session=MagicMock(),
        save_project_session=MagicMock(),
        record_command=MagicMock(),
    )


def make_runtime():
    return SimpleNamespace(
        client=object(),
        reset_messages=MagicMock(),
        run_task=MagicMock(return_value="task result"),
    )


class CliTests(unittest.TestCase):
    def test_run_configured_cmd_executes_mapped_command_with_args(self):
        with patch("openrouter_agent.cli.config.load_cmd_commands", return_value={"dir": "dir"}), patch(
            "openrouter_agent.cli.config.load_cmd_commands_file", return_value={}
        ), patch(
            "openrouter_agent.cli.run_shell_command", return_value="ok"
        ) as mock_run:
            result = cli.run_configured_cmd("dir src")
        self.assertEqual("ok", result)
        mock_run.assert_called_once_with("dir src", allowed_binaries={"dir"})

    def test_run_configured_cmd_reports_unknown_name(self):
        with patch("openrouter_agent.cli.config.load_cmd_commands", return_value={"pwd": "pwd"}), patch(
            "openrouter_agent.cli.config.load_cmd_commands_file", return_value={}
        ):
            result = cli.run_configured_cmd("dir")
        self.assertIn("Unknown configured command: dir", result)

    def test_add_configured_cmd_saves_mapping(self):
        with patch("openrouter_agent.cli.config.add_cmd_command", return_value="whoami") as mock_add, patch(
            "openrouter_agent.cli.project_cmd_commands_file", return_value="workspace/alpha/.cmd_commands.json"
        ):
            result = cli.add_configured_cmd("whoami whoami")
        self.assertEqual("Project command saved: whoami -> whoami", result)
        mock_add.assert_called_once_with("whoami", "whoami", path="workspace/alpha/.cmd_commands.json")

    def test_add_configured_cmd_requires_name_and_command(self):
        result = cli.add_configured_cmd("whoami")
        self.assertEqual("Usage: /cmdadd NAME COMMAND", result)

    def test_remove_configured_cmd_removes_mapping(self):
        with patch("openrouter_agent.cli.config.remove_cmd_command", return_value="pwd") as mock_remove, patch(
            "openrouter_agent.cli.project_cmd_commands_file", return_value="workspace/alpha/.cmd_commands.json"
        ):
            result = cli.remove_configured_cmd("pwd")
        self.assertEqual("Project command removed: pwd", result)
        mock_remove.assert_called_once_with("pwd", path="workspace/alpha/.cmd_commands.json")

    def test_remove_configured_cmd_reports_unknown_name(self):
        with patch("openrouter_agent.cli.config.remove_cmd_command", side_effect=KeyError("pwd")), patch(
            "openrouter_agent.cli.config.load_cmd_commands", return_value={"dir": "dir"}
        ), patch(
            "openrouter_agent.cli.config.load_cmd_commands_file", return_value={}
        ):
            result = cli.remove_configured_cmd("pwd")
        self.assertIn("Unknown configured command: pwd", result)

    def test_remove_configured_cmd_reports_inherited_repo_command(self):
        with patch("openrouter_agent.cli.config.remove_cmd_command", side_effect=KeyError("pwd")), patch(
            "openrouter_agent.cli.config.load_cmd_commands", return_value={"pwd": "pwd"}
        ):
            result = cli.remove_configured_cmd("pwd")
        self.assertIn("inherited from the repo-level .cmd_commands.json", result)

    def test_active_cmd_commands_merges_repo_and_project_commands(self):
        with patch("openrouter_agent.cli.config.load_cmd_commands", return_value={"pwd": "pwd", "dir": "dir"}), patch(
            "openrouter_agent.cli.config.load_cmd_commands_file", return_value={"pwd": "project-pwd", "cat": "cat"}
        ):
            commands = cli.active_cmd_commands()
        self.assertEqual({"pwd": "project-pwd", "dir": "dir", "cat": "cat"}, commands)

    def test_handle_exact_cmd_without_args_shows_usage(self):
        state = make_state()
        runtime = make_runtime()
        with patch("builtins.print") as mock_print:
            handled = cli.handle_exact_command("/cmd", state, runtime)
        self.assertTrue(handled)
        self.assertGreaterEqual(mock_print.call_count, 2)

    def test_handle_exact_cmdlist_shows_configured_commands(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.configured_cmds_text", return_value="dir -> dir"), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_exact_command("/cmdlist", state, runtime)
        self.assertTrue(handled)
        self.assertEqual(2, mock_print.call_count)

    def test_handle_prefixed_cmdadd_prints_result(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.add_configured_cmd", return_value="saved"), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_prefixed_command("/cmdadd pwd pwd", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("saved")

    def test_handle_prefixed_cmddel_prints_result(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.remove_configured_cmd", return_value="removed"), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_prefixed_command("/cmddel pwd", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("removed")

    def test_help_topic_text_resolves_models_command(self):
        text = cli.help_topic_text("models")
        self.assertIn("/models", text)
        self.assertIn("Show selected provider::model routes", text)

    def test_handle_prefixed_help_prints_specific_command_help(self):
        state = make_state()
        runtime = make_runtime()
        with patch("builtins.print") as mock_print:
            handled = cli.handle_prefixed_command("/help models", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once()

    def test_projects_text_marks_active_project(self):
        with patch("openrouter_agent.cli.list_projects", return_value=["alpha", "beta"]):
            text = cli.projects_text("beta")
        self.assertIn("  alpha", text)
        self.assertIn("* beta (active)", text)

    def test_handle_exact_command_discoverfull_uses_full_scan(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.discover_routes", return_value=["r2", "r1"]) as mock_discover, patch(
            "openrouter_agent.cli.rank_routes", side_effect=lambda routes: routes
        ), patch("openrouter_agent.cli.MultiProviderClient", return_value="client"), patch(
            "builtins.print"
        ), patch("openrouter_agent.cli.ui.success"), patch("openrouter_agent.cli.ui.info"):
            handled = cli.handle_exact_command("/discoverfull", state, runtime)

        self.assertTrue(handled)
        mock_discover.assert_called_once_with(max_checks=0, use_cache=False, early_stop=False)
        self.assertEqual(["r2", "r1"], state.routes)
        state.save_project_session.assert_called_once()

    def test_handle_prefixed_command_switches_project(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.set_active_project", return_value="beta"), patch(
            "openrouter_agent.cli.current_project_root", return_value="C:/workspace/beta"
        ), patch(
            "openrouter_agent.cli.load_prompt_history"
        ), patch("openrouter_agent.cli.MultiProviderClient", return_value="client"), patch(
            "openrouter_agent.cli.ui.success"
        ), patch("openrouter_agent.cli.ui.info"):
            handled = cli.handle_prefixed_command("/project beta", state, runtime)

        self.assertTrue(handled)
        self.assertEqual("beta", state.active_project)
        state.load_project_session.assert_called_once()
        runtime.reset_messages.assert_called_once()
        state.save_project_session.assert_called_once()

    def test_activate_project_reloads_prompt_history_for_project(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.create_project", return_value="beta"), patch(
            "openrouter_agent.cli.current_project_root", return_value="C:/workspace/beta"
        ), patch("openrouter_agent.cli.load_prompt_history") as mock_history, patch(
            "openrouter_agent.cli.MultiProviderClient", return_value="client"
        ), patch("openrouter_agent.cli.ui.success"), patch("openrouter_agent.cli.ui.info"):
            cli.activate_project(state, runtime, "beta", cli.create_project)

        self.assertEqual("beta", state.active_project)
        state.load_project_session.assert_called_once()
        mock_history.assert_called_once_with(state)

    def test_activate_project_clears_command_history_before_loading_new_project(self):
        state = make_state()
        state.command_history = ["/models", "/discover"]
        runtime = make_runtime()

        def fake_load():
            return False

        state.load_project_session = MagicMock(side_effect=fake_load)
        with patch("openrouter_agent.cli.create_project", return_value="beta"), patch(
            "openrouter_agent.cli.current_project_root", return_value="C:/workspace/beta"
        ), patch("openrouter_agent.cli.load_prompt_history"), patch(
            "openrouter_agent.cli.MultiProviderClient", return_value="client"
        ), patch("openrouter_agent.cli.ui.success"), patch("openrouter_agent.cli.ui.info"):
            cli.activate_project(state, runtime, "beta", cli.create_project)

        self.assertEqual([], state.command_history)

    def test_handle_prefixed_command_updates_provider_and_persists(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.ui.info"):
            handled = cli.handle_prefixed_command("/provider huggingface", state, runtime)
        self.assertTrue(handled)
        self.assertEqual("huggingface", state.provider_mode)
        state.save_project_session.assert_called_once()

    def test_apply_profile_supports_mistral(self):
        state = make_state()
        result = cli.apply_profile(state, "mistral")
        self.assertEqual("Profile activated: mistral", result)
        self.assertEqual("mistral", state.provider_mode)

    def test_handle_exact_command_mistralmodels_prints_models(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.get_mistral_models", return_value=["mistral-small-latest"]), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_exact_command("/mistralmodels", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("mistral-small-latest")

    def test_handle_prefixed_command_addmistralmodel(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.add_mistral_model", return_value="Added Mistral model: codestral-latest"), patch(
            "openrouter_agent.cli.ui.info"
        ) as mock_info, patch("builtins.print") as mock_print:
            handled = cli.handle_prefixed_command("/addmistralmodel codestral-latest", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("Added Mistral model: codestral-latest")
        mock_info.assert_called_once()

    def test_handle_prefixed_command_removemistralmodel(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.remove_mistral_model", return_value="Removed Mistral model: codestral-latest"), patch(
            "openrouter_agent.cli.ui.info"
        ) as mock_info, patch("builtins.print") as mock_print:
            handled = cli.handle_prefixed_command("/removemistralmodel codestral-latest", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("Removed Mistral model: codestral-latest")
        mock_info.assert_called_once()

    def test_handle_exact_command_gitsafedir_prints_result(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.git_safe_directory", return_value="safe dir help"), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_exact_command("/gitsafedir", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("safe dir help")

    def test_handle_exact_command_gitsafedir_apply_prints_result(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.git_safe_directory", return_value="applied"), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_prefixed_command("/gitsafedir apply", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("applied")

    def test_command_history_text_formats_saved_commands(self):
        state = make_state()
        state.command_history = ["/models", "/discover"]
        text = cli.command_history_text(state)
        self.assertIn("Saved command history", text)
        self.assertIn("1. /models", text)
        self.assertIn("2. /discover", text)

    def test_handle_exact_command_cmdhistory_prints_history(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.command_history_text", return_value="history text"), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_exact_command("/cmdhistory", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("history text")

    def test_load_prompt_history_replaces_readline_history(self):
        state = make_state()
        state.command_history = ["/models", "/discover"]
        fake_readline = MagicMock()
        with patch("openrouter_agent.cli.readline", fake_readline):
            loaded = cli.load_prompt_history(state)
        self.assertTrue(loaded)
        fake_readline.clear_history.assert_called_once()
        fake_readline.set_history_length.assert_called_once()
        fake_readline.add_history.assert_any_call("/models")
        fake_readline.add_history.assert_any_call("/discover")

    def test_append_prompt_history_skips_duplicate_last_entry(self):
        fake_readline = MagicMock()
        fake_readline.get_current_history_length.return_value = 1
        fake_readline.get_history_item.return_value = "/models"
        with patch("openrouter_agent.cli.readline", fake_readline):
            appended = cli.append_prompt_history("/models")
        self.assertTrue(appended)
        fake_readline.add_history.assert_not_called()

    def test_handle_command_returns_false_for_unknown_command(self):
        state = make_state()
        runtime = make_runtime()
        handled = cli.handle_command("/unknowncmd", state, runtime)
        self.assertFalse(handled)


if __name__ == "__main__":
    unittest.main()
