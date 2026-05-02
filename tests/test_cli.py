import json
import unittest
import uuid
from pathlib import Path
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


def make_tmp_root(prefix: str) -> Path:
    root = Path("workspace") / f"{prefix}-{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=False)
    return root


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

    def test_handle_prefixed_command_updates_temperature_and_persists(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.ui.info"):
            handled = cli.handle_prefixed_command("/temperature 0.7", state, runtime)
        self.assertTrue(handled)
        self.assertEqual(0.7, state.temperature)
        state.save_project_session.assert_called_once()

    def test_handle_prefixed_command_rejects_invalid_temperature(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.ui.warn") as mock_warn:
            handled = cli.handle_prefixed_command("/temperature 3.5", state, runtime)
        self.assertTrue(handled)
        self.assertEqual(0.2, state.temperature)
        mock_warn.assert_called_once()

    def test_handle_prefixed_command_taskresume_prints_result(self):
        state = make_state()
        runtime = make_runtime()
        runtime.resume_task = MagicMock(return_value="resumed")
        with patch("builtins.print") as mock_print:
            handled = cli.handle_prefixed_command("/taskresume 123", state, runtime)
        self.assertTrue(handled)
        runtime.resume_task.assert_called_once_with("123")
        mock_print.assert_called_once_with("resumed")

    def test_parse_taskretry_requires_task_id(self):
        task_id, overrides, err = cli.parse_taskretry("")
        self.assertIsNone(task_id)
        self.assertIsNotNone(err)

    def test_parse_taskretry_parses_overrides(self):
        task_id, overrides, err = cli.parse_taskretry("abc --tooliters 40 --provider mistral --review off --safe")
        self.assertIsNone(err)
        self.assertEqual("abc", task_id)
        self.assertEqual(40, overrides["max_tool_iterations"])
        self.assertEqual("mistral", overrides["provider_mode"])
        self.assertFalse(overrides["review_enabled"])
        self.assertTrue(overrides["retry_safe_mode"])

    def test_taskretry_applies_overrides_temporarily(self):
        state = make_state()
        runtime = make_runtime()
        runtime.run_task = MagicMock(return_value="retry done")
        state.provider_mode = "auto"
        state.max_tool_iterations = 25
        state.review_enabled = True
        state.retry_safe_mode = False
        checkpoint = {"user_input": "fix bug"}
        with patch("openrouter_agent.cli.load_checkpoint", return_value=checkpoint):
            result = cli.taskretry(runtime, state, "run1 --tooliters 40 --provider mistral --review off --safe")
        self.assertEqual("retry done", result)
        runtime.run_task.assert_called_once_with("fix bug")
        self.assertEqual("auto", state.provider_mode)
        self.assertEqual(25, state.max_tool_iterations)
        self.assertTrue(state.review_enabled)
        self.assertFalse(state.retry_safe_mode)

    def test_handle_prefixed_command_taskretry_prints_result(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.taskretry", return_value="retried"), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_prefixed_command("/taskretry run1", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("retried")

    def test_handle_exact_command_runs_prints_rows(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.runs_text", return_value="Checkpointed runs"), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_exact_command("/runs", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("Checkpointed runs")

    def test_handle_exact_command_subagents_prints_roles(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.subagents_text", return_value="Available subagents: review, search"), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_exact_command("/subagents", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("Available subagents: review, search")

    def test_handle_prefixed_command_asksubagent_prints_result(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.build_subagent_context", return_value={"task_id": "t1"}), patch(
            "openrouter_agent.cli.run_subagent", return_value={"content": "subagent result"}
        ), patch(
            "openrouter_agent.cli.ui.panel"
        ) as mock_panel:
            handled = cli.handle_prefixed_command("/asksubagent review \"check this file\" --task t1", state, runtime)
        self.assertTrue(handled)
        mock_panel.assert_called_once()

    def test_run_plan_file_executes_asksubagent_lines(self):
        state = make_state()
        runtime = make_runtime()
        with patch(
            "openrouter_agent.cli.read_text_file",
            return_value=(
                "# plan\n"
                "/asksubagent plan \"Design the app.\"\n"
                "\n"
                "/asksubagent review \"Review the design.\"\n"
            ),
        ), patch("openrouter_agent.cli.handle_prefixed_command", return_value=True) as mock_handle, patch(
            "openrouter_agent.cli.ui.panel"
        ) as mock_panel:
            result = cli.run_plan_file(runtime, state, "workspace/alpha/subagent_plan.md")

        self.assertEqual("Plan completed. Executed 2 subagent command(s).", result)
        self.assertEqual(2, mock_handle.call_count)
        mock_panel.assert_called()

    def test_run_plan_file_rejects_non_subagent_lines(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.read_text_file", return_value="/help\n"):
            result = cli.run_plan_file(runtime, state, "workspace/alpha/subagent_plan.md")
        self.assertIn("Plan file can only contain /asksubagent commands.", result)

    def test_handle_prefixed_command_runplan_prints_result(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.run_plan_file", return_value="Plan completed."), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_prefixed_command("/runplan subagent_plan.md", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("Plan completed.")

    def test_parse_asksubagent_spec_parses_task_and_prompt(self):
        role, prompt, task_id, include_task_context, target_file, scope_path, preview, err = cli.parse_asksubagent_spec('review "check this file" --task t1')
        self.assertIsNone(err)
        self.assertEqual("review", role)
        self.assertEqual("check this file", prompt)
        self.assertEqual("t1", task_id)
        self.assertTrue(include_task_context)
        self.assertIsNone(target_file)
        self.assertIsNone(scope_path)
        self.assertFalse(preview)

    def test_parse_asksubagent_spec_supports_no_task(self):
        role, prompt, task_id, include_task_context, target_file, scope_path, preview, err = cli.parse_asksubagent_spec('search "find symbols" --no-task')
        self.assertIsNone(err)
        self.assertEqual("search", role)
        self.assertEqual("find symbols", prompt)
        self.assertIsNone(task_id)
        self.assertFalse(include_task_context)
        self.assertIsNone(target_file)
        self.assertIsNone(scope_path)
        self.assertFalse(preview)

    def test_parse_asksubagent_spec_supports_worker_file(self):
        role, prompt, task_id, include_task_context, target_file, scope_path, preview, err = cli.parse_asksubagent_spec(
            'worker --file app.py "add docs" --preview'
        )
        self.assertIsNone(err)
        self.assertEqual("worker", role)
        self.assertEqual("add docs", prompt)
        self.assertIsNone(task_id)
        self.assertTrue(include_task_context)
        self.assertEqual("app.py", target_file)
        self.assertIsNone(scope_path)
        self.assertTrue(preview)

    def test_parse_asksubagent_spec_supports_worker_scope(self):
        role, prompt, task_id, include_task_context, target_file, scope_path, preview, err = cli.parse_asksubagent_spec(
            'worker --scope src "update docs"'
        )
        self.assertIsNone(err)
        self.assertEqual("worker", role)
        self.assertEqual("update docs", prompt)
        self.assertIsNone(task_id)
        self.assertTrue(include_task_context)
        self.assertIsNone(target_file)
        self.assertEqual("src", scope_path)
        self.assertFalse(preview)

    def test_handle_prefixed_command_worker_routes_to_worker_helper(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.run_worker_subagent", return_value="Changes kept." ) as mock_worker, patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_prefixed_command('/asksubagent worker --file app.py "add docs"', state, runtime)
        self.assertTrue(handled)
        mock_worker.assert_called_once()
        mock_print.assert_called_once_with("Changes kept.")

    def test_run_worker_subagent_applies_confirmed_file_change(self):
        state = make_state()
        runtime = make_runtime()
        runtime.client = object()
        payload = {
            "target_file": "app.py",
            "summary": "Add one line.",
            "patches": [
                {"start_line": 2, "end_line": 2, "new_text": "line2 updated"},
            ],
        }
        root = make_tmp_root("worker-confirm")
        (root / "app.py").write_text("line1\nline2\n", encoding="utf-8")
        try:
            with patch("openrouter_agent.tools.files.current_project_root", return_value=root), patch(
                "openrouter_agent.tools.files.safe_path", side_effect=lambda path: root / str(path)
            ), patch(
                "openrouter_agent.cli.read_text_file", side_effect=["line1\nline2\n", "line1\nline2\n"]
            ), patch(
                "openrouter_agent.cli.read_file_with_line_numbers", return_value="    1: line1\n    2: line2"
            ), patch(
                "openrouter_agent.cli.run_subagent", return_value={"content": json.dumps(payload)}
            ), patch("openrouter_agent.cli.input", return_value="y"), patch(
                "openrouter_agent.cli.build_subagent_context", return_value={"task_id": "t1"}
            ), patch("openrouter_agent.cli.ui.table") as mock_table, patch(
                "openrouter_agent.cli.export_worker_patch_file", return_value=Path("C:/scope/patch.patch")
            ):
                result = cli.run_worker_subagent(runtime, state, 'worker --file app.py "add line"')

            self.assertEqual("Changes kept. Patch export: C:\\scope\\patch.patch", result)
            mock_table.assert_called_once()
        finally:
            if root.exists():
                for child in sorted(root.rglob("*"), reverse=True):
                    if child.is_file():
                        child.unlink()
                for child in sorted([p for p in root.rglob("*") if p.is_dir()], reverse=True):
                    child.rmdir()
                root.rmdir()

    def test_run_worker_subagent_can_create_new_files(self):
        state = make_state()
        runtime = make_runtime()
        runtime.client = object()
        payload = {
            "scope": ".",
            "summary": "Create the scaffold.",
            "patches": [
                {
                    "target_file": "main.py",
                    "start_line": 0,
                    "end_line": 0,
                    "new_text": "from tkinter_app import main\n\nif __name__ == \"__main__\":\n    main()\n",
                },
                {
                    "target_file": "tkinter_app.py",
                    "start_line": 0,
                    "end_line": 0,
                    "new_text": "\"\"\"Launcher.\"\"\"\n",
                },
            ],
        }
        root = make_tmp_root("worker-create")
        try:
            with patch("openrouter_agent.tools.files.current_project_root", return_value=root), patch(
                "openrouter_agent.tools.files.safe_path", side_effect=lambda path: root / str(path)
            ), patch(
                "openrouter_agent.cli.run_subagent", return_value={"content": json.dumps(payload)}
            ), patch("openrouter_agent.cli.build_subagent_context", return_value={"task_id": "t1"}), patch(
                "openrouter_agent.cli.ui.table"
            ), patch("openrouter_agent.cli.input", return_value="y"), patch(
                "openrouter_agent.cli.export_worker_patch_file", return_value=Path("C:/scope/patch.patch")
            ):
                result = cli.run_worker_subagent(runtime, state, 'worker --scope . "create scaffold"')

            self.assertIn("Changes kept.", result)
            self.assertEqual("from tkinter_app import main\n\nif __name__ == \"__main__\":\n    main()\n", (root / "main.py").read_text(encoding="utf-8"))
            self.assertEqual("\"\"\"Launcher.\"\"\"\n", (root / "tkinter_app.py").read_text(encoding="utf-8"))
        finally:
            if root.exists():
                for child in sorted(root.rglob("*"), reverse=True):
                    if child.is_file():
                        child.unlink()
                for child in sorted([p for p in root.rglob("*") if p.is_dir()], reverse=True):
                    child.rmdir()
                root.rmdir()

    def test_parse_worker_patch_payload_parses_json_patches(self):
        payload = cli.parse_worker_patch_payload(json.dumps({
            "target_file": "app.py",
            "summary": "Update line.",
            "patches": [{"start_line": 1, "end_line": 1, "new_text": "line1", "create_file": False}],
        }))
        self.assertEqual("app.py", payload["target_file"])
        self.assertEqual("Update line.", payload["summary"])
        self.assertEqual(1, len(payload["patches"]))
        self.assertFalse(payload["patches"][0]["create_file"])

    def test_validate_worker_patch_payload_replaces_requested_range(self):
        root = make_tmp_root("validate-existing")
        (root / "app.py").write_text("line1\nline2\n", encoding="utf-8")
        try:
            with patch("openrouter_agent.tools.files.safe_path") as mock_safe:
                mock_safe.side_effect = lambda path: root / str(path)
                resolved = cli.validate_worker_patch_payload(
                    {"app.py": "line1\nline2\n"},
                    {
                        "target_file": "app.py",
                        "patches": [{"target_file": "app.py", "start_line": 2, "end_line": 2, "new_text": "line2 updated"}],
                    },
                    "app.py",
                    root,
                )
                updated = cli.apply_worker_patch_payload(
                    {"app.py": "line1\nline2\n"},
                    resolved,
                    root,
                )["app.py"]
        finally:
            if root.exists():
                for child in sorted(root.rglob("*"), reverse=True):
                    if child.is_file():
                        child.unlink()
                for child in sorted([p for p in root.rglob("*") if p.is_dir()], reverse=True):
                    child.rmdir()
                root.rmdir()
        self.assertEqual("line1\nline2 updated\n", updated)

    def test_validate_worker_patch_payload_supports_multiple_targets_inside_scope(self):
        root = make_tmp_root("validate-multi")
        (root / "src").mkdir(parents=True, exist_ok=False)
        (root / "src" / "a.py").write_text("a1\na2\n", encoding="utf-8")
        (root / "src" / "b.py").write_text("b1\n", encoding="utf-8")
        try:
            with patch("openrouter_agent.tools.files.safe_path") as mock_safe:
                mock_safe.side_effect = lambda path: root / str(path)
                resolved = cli.validate_worker_patch_payload(
                    {"src/a.py": "a1\na2\n", "src/b.py": "b1\n"},
                    {
                        "scope": "src",
                        "patches": [
                            {"target_file": "src/a.py", "start_line": 2, "end_line": 2, "new_text": "a2 updated"},
                            {"target_file": "src/b.py", "start_line": 1, "end_line": 1, "new_text": "b1 updated"},
                        ],
                    },
                    "src",
                    root / "src",
                )
                updated_map = cli.apply_worker_patch_payload(
                    {"src/a.py": "a1\na2\n", "src/b.py": "b1\n"},
                    resolved,
                    root / "src",
                )
        finally:
            if root.exists():
                for child in sorted(root.rglob("*"), reverse=True):
                    if child.is_file():
                        child.unlink()
                for child in sorted([p for p in root.rglob("*") if p.is_dir()], reverse=True):
                    child.rmdir()
                root.rmdir()

        self.assertEqual("a1\na2 updated\n", updated_map["src/a.py"])
        self.assertEqual("b1 updated\n", updated_map["src/b.py"])

    def test_validate_worker_patch_payload_allows_new_file_creation(self):
        root = make_tmp_root("validate-create")
        try:
            with patch("openrouter_agent.tools.files.safe_path") as mock_safe:
                mock_safe.side_effect = lambda path: root / str(path)
                resolved = cli.validate_worker_patch_payload(
                    {},
                    {
                        "scope": ".",
                        "patches": [
                            {
                                "target_file": "main.py",
                                "start_line": 0,
                                "end_line": 0,
                                "new_text": "print('hello')\n",
                            }
                        ],
                    },
                    ".",
                    root,
                )
                updated_map = cli.apply_worker_patch_payload({}, resolved, root)
        finally:
            if root.exists():
                for child in sorted(root.rglob("*"), reverse=True):
                    if child.is_file():
                        child.unlink()
                for child in sorted([p for p in root.rglob("*") if p.is_dir()], reverse=True):
                    child.rmdir()
                root.rmdir()

        self.assertEqual("print('hello')\n", updated_map["main.py"])

    def test_worker_patch_preview_rows_summarizes_files(self):
        rows = cli.worker_patch_preview_rows(
            {"summary": "Update docs."},
            [
                ("src/a.py", {"start_line": 1, "end_line": 2}),
                ("src/a.py", {"start_line": 5, "end_line": 5}),
                ("src/b.py", {"start_line": 3, "end_line": 4}),
            ],
            {"src/a.py": "x", "src/b.py": "y"},
        )
        self.assertIn(("Summary", "Update docs."), rows)
        self.assertIn(("Patch count", 3), rows)
        self.assertIn(("src/a.py", "2 patch(es); lines 1-2, 5-5"), rows)
        self.assertIn(("src/b.py", "1 patch(es); lines 3-4"), rows)

    def test_export_worker_patch_file_writes_patch_export(self):
        from pathlib import Path

        with patch(
            "openrouter_agent.project_context.project_log_dir",
            return_value=Path("C:/Varios/IA/TinyAgent/openrouter-agent-v21-production/logs/alpha"),
        ), patch(
            "pathlib.Path.write_text"
        ) as mock_write:
            out = cli.export_worker_patch_file(
                {"target_file": "app.py", "summary": "Update."},
                [("app.py", {"start_line": 1, "end_line": 1, "new_text": "line1"})],
            )

        self.assertTrue(str(out).endswith(".patch"))
        mock_write.assert_called_once()

    def test_subagent_result_text_formats_metadata_and_content(self):
        text = cli.subagent_result_text({
            "role": "review",
            "route": "openrouter::model",
            "provider": "openrouter",
            "model": "model",
            "content": "Looks fine.",
        })
        self.assertIn("Role: review", text)
        self.assertIn("Route: openrouter::model", text)
        self.assertIn("Looks fine.", text)

    def test_handle_prefixed_command_run_prints_checkpoint(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.load_checkpoint", return_value={"task_id": "run1"}), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_prefixed_command("/run run1", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once()

    def test_handle_prefixed_command_runclear(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.delete_checkpoint", return_value=True), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_prefixed_command("/runclear run1", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("Checkpoint deleted: run1")

    def test_handle_exact_command_runclearall(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.clear_checkpoints", return_value=2), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_exact_command("/runclearall", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("Deleted 2 checkpoint(s).")

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

    def test_handle_prefixed_command_edit_prints_result(self):
        state = make_state()
        runtime = make_runtime()
        with patch("openrouter_agent.cli.run_edit_file", return_value="Changes kept."), patch(
            "builtins.print"
        ) as mock_print:
            handled = cli.handle_prefixed_command("/edit app.py", state, runtime)
        self.assertTrue(handled)
        mock_print.assert_called_once_with("Changes kept.")

    def test_parse_edit_spec_parses_instruction_and_preview(self):
        target, instruction, preview, err = cli.parse_edit_spec('app.py --instruction "add docs" --preview')
        self.assertIsNone(err)
        self.assertEqual("app.py", target)
        self.assertEqual("add docs", instruction)
        self.assertTrue(preview)

    def test_run_edit_file_with_instruction_uses_provided_instruction(self):
        state = make_state()
        runtime = make_runtime()
        runtime.state = state
        runtime.run_task = MagicMock(return_value="task result")
        with patch("openrouter_agent.cli.read_text_file", side_effect=["line1\n", "line1\nline2\n"]), patch(
            "openrouter_agent.cli.input", return_value="y"
        ):
            result = cli.run_edit_file(runtime, 'allowed.txt --instruction "add line"')
        self.assertEqual("Changes kept.", result)
        runtime.run_task.assert_called_once()
        prompt = runtime.run_task.call_args[0][0]
        self.assertIn("Target file: allowed.txt", prompt)
        self.assertIn("Edit request: add line", prompt)

    def test_run_edit_file_preview_returns_no_changes_applied(self):
        state = make_state()
        runtime = make_runtime()
        runtime.state = state
        runtime.run_task = MagicMock(return_value="preview result")
        with patch("openrouter_agent.cli.read_text_file", return_value="line1\n"), patch(
            "openrouter_agent.cli.input"
        ) as mock_input:
            result = cli.run_edit_file(runtime, 'allowed.txt --instruction "add line" --preview')
        self.assertIn("Preview complete. No changes applied.", result)
        self.assertEqual("preview result", result.splitlines()[-1])
        mock_input.assert_not_called()
        self.assertFalse(state.dry_run)

    def test_run_edit_file_restores_previous_edit_target(self):
        state = make_state()
        state.edit_target_file = "existing.txt"
        runtime = make_runtime()
        runtime.state = state
        runtime.run_task = MagicMock(return_value="task result")
        with patch("openrouter_agent.cli.read_text_file", side_effect=["line1\n", "line1\nline2\n"]), patch(
            "openrouter_agent.cli.input", side_effect=["add line", "y"]
        ):
            result = cli.run_edit_file(runtime, "allowed.txt")
        self.assertEqual("Changes kept.", result)
        self.assertEqual("existing.txt", state.edit_target_file)

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
