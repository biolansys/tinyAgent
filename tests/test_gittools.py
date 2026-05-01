import unittest
from unittest.mock import patch

from openrouter_agent import gittools


class CompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class GitToolsTests(unittest.TestCase):
    def test_run_git_refuses_parent_repository_fallback(self):
        with patch("openrouter_agent.gittools._project_has_own_git_repo", return_value=False):
            result = gittools.git_status()
        self.assertEqual(
            "Git command unavailable: the active project is not initialized as its own git repository.",
            result,
        )

    def test_git_log_uses_requested_limit(self):
        calls = []

        def fake_run(cmd, cwd, capture_output, text, timeout):
            calls.append(cmd)
            return CompletedProcess(stdout="abc123 commit\n")

        with patch("openrouter_agent.gittools._project_has_own_git_repo", return_value=True), patch(
            "openrouter_agent.gittools.subprocess.run", side_effect=fake_run
        ):
            result = gittools.git_log(5)

        self.assertIn(["git", "log", "-n5", "--oneline", "--decorate"], calls)
        self.assertIn("abc123 commit", result)

    def test_git_show_defaults_to_head(self):
        calls = []

        def fake_run(cmd, cwd, capture_output, text, timeout):
            calls.append(cmd)
            return CompletedProcess(stdout="abc123 HEAD\n")

        with patch("openrouter_agent.gittools._project_has_own_git_repo", return_value=True), patch(
            "openrouter_agent.gittools.subprocess.run", side_effect=fake_run
        ):
            result = gittools.git_show()

        self.assertIn(["git", "show", "--stat", "--oneline", "HEAD", "--"], calls)
        self.assertIn("abc123 HEAD", result)

    def test_git_status_empty_output_means_clean_worktree(self):
        with patch("openrouter_agent.gittools._project_has_own_git_repo", return_value=True), patch(
            "openrouter_agent.gittools.subprocess.run",
            return_value=CompletedProcess(returncode=0, stdout="", stderr=""),
        ):
            result = gittools.git_status()
        self.assertEqual("Working tree clean.", result)

    def test_git_files_clean_worktree(self):
        with patch("openrouter_agent.gittools.git_status", return_value="Working tree clean."):
            result = gittools.git_files()
        self.assertEqual("No changed files.", result)

    def test_git_commit_dry_returns_status_and_diff(self):
        with patch("openrouter_agent.gittools.git_status", return_value=" M example.py"), patch(
            "openrouter_agent.gittools.git_diff", return_value="diff --git a/example.py b/example.py"
        ):
            result = gittools.git_commit_dry()
        self.assertIn("Project status:", result)
        self.assertIn("Project diff preview:", result)

    def test_git_commit_dry_clean_worktree(self):
        with patch("openrouter_agent.gittools.git_status", return_value="Working tree clean."):
            result = gittools.git_commit_dry()
        self.assertEqual("No project changes to preview.", result)

    def test_git_diff_cached_uses_cached_diff(self):
        calls = []

        def fake_run(cmd, cwd, capture_output, text, timeout):
            calls.append(cmd)
            return CompletedProcess(stdout="cached diff\n")

        with patch("openrouter_agent.gittools._project_has_own_git_repo", return_value=True), patch(
            "openrouter_agent.gittools.subprocess.run", side_effect=fake_run
        ):
            result = gittools.git_diff_cached()

        self.assertIn(["git", "diff", "--cached", "--", "."], calls)
        self.assertIn("cached diff", result)

    def test_git_add_runs_after_confirmation(self):
        calls = []

        def fake_run(cmd, cwd, capture_output, text, timeout):
            calls.append(cmd)
            return CompletedProcess(stdout="ok\n")

        with patch("openrouter_agent.gittools.git_status", return_value=" M example.py"), patch(
            "openrouter_agent.gittools._project_has_own_git_repo", return_value=True
        ), patch("openrouter_agent.gittools._confirm_git_action", return_value=True), patch(
            "openrouter_agent.gittools.subprocess.run", side_effect=fake_run
        ):
            result = gittools.git_add()

        self.assertIn(["git", "add", "--", "."], calls)
        self.assertIn("ok", result)

    def test_git_unstage_runs_after_confirmation(self):
        calls = []

        def fake_run(cmd, cwd, capture_output, text, timeout):
            calls.append(cmd)
            return CompletedProcess(stdout="ok\n")

        with patch("openrouter_agent.gittools.git_status", return_value="M  example.py"), patch(
            "openrouter_agent.gittools._project_has_own_git_repo", return_value=True
        ), patch("openrouter_agent.gittools._confirm_git_action", return_value=True), patch(
            "openrouter_agent.gittools.subprocess.run", side_effect=fake_run
        ):
            result = gittools.git_unstage()

        self.assertIn(["git", "restore", "--staged", "--", "."], calls)
        self.assertIn("ok", result)

    def test_git_restore_cancelled_without_confirmation(self):
        with patch("openrouter_agent.gittools.git_status", return_value=" M example.py"), patch(
            "openrouter_agent.gittools._confirm_git_action", return_value=False
        ):
            result = gittools.git_restore()
        self.assertEqual("Git action cancelled.", result)

    def test_git_restore_runs_restore_commands(self):
        calls = []

        def fake_run(cmd, cwd, capture_output, text, timeout):
            calls.append(cmd)
            return CompletedProcess(stdout="ok\n")

        with patch("openrouter_agent.gittools._project_has_own_git_repo", return_value=True), patch(
            "openrouter_agent.gittools.git_status", return_value=" M example.py"
        ), patch(
            "openrouter_agent.gittools._confirm_git_action", return_value=True
        ), patch("openrouter_agent.gittools.subprocess.run", side_effect=fake_run):
            result = gittools.git_restore()

        self.assertIn(["git", "restore", "--staged", "--worktree", "--", "."], calls)
        self.assertIn(["git", "restore", "--worktree", "--", "."], calls)
        self.assertIn("ok", result)

    def test_git_restore_file_uses_relative_path(self):
        calls = []

        def fake_run(cmd, cwd, capture_output, text, timeout):
            calls.append(cmd)
            return CompletedProcess(stdout="ok\n")

        project_root = gittools.config.ROOT / "workspace" / "alpha"
        fake_path = project_root / "src" / "app.py"
        with patch("openrouter_agent.gittools._project_has_own_git_repo", return_value=True), patch(
            "openrouter_agent.gittools.git_status", return_value=" M src/app.py"
        ), patch("openrouter_agent.gittools.safe_path", return_value=fake_path), patch(
            "openrouter_agent.gittools.current_project_root", return_value=project_root
        ), patch("openrouter_agent.gittools._confirm_git_action", return_value=True), patch(
            "openrouter_agent.gittools.subprocess.run", side_effect=fake_run
        ):
            result = gittools.git_restore("src/app.py")

        self.assertIn(["git", "restore", "--staged", "--worktree", "--", "src/app.py"], calls)
        self.assertIn(["git", "restore", "--worktree", "--", "src/app.py"], calls)
        self.assertIn("ok", result)

    def test_git_init_returns_existing_repo_message(self):
        fake_root = gittools.config.ROOT / "fake-project"
        with patch("openrouter_agent.gittools.current_project_root", return_value=fake_root), patch(
            "pathlib.Path.exists", return_value=True
        ):
            result = gittools.git_init()
        self.assertEqual("Git repository already initialized.", result)

    def test_git_init_runs_after_confirmation(self):
        calls = []

        def fake_run(cmd, cwd, capture_output, text, timeout):
            calls.append(cmd)
            return CompletedProcess(stdout="Initialized empty Git repository\n")

        fake_root = gittools.config.ROOT / "fake-project"
        with patch("openrouter_agent.gittools.current_project_root", return_value=fake_root), patch(
            "pathlib.Path.exists", return_value=False
        ), patch("openrouter_agent.gittools._confirm_git_action", return_value=True), patch(
            "openrouter_agent.gittools._project_has_own_git_repo", return_value=False
        ), patch(
            "openrouter_agent.gittools.subprocess.run", side_effect=fake_run
        ):
            result = gittools.git_init()

        self.assertIn(["git", "init"], calls)
        self.assertIn("Initialized empty Git repository", result)

    def test_run_git_reports_missing_repository_clearly(self):
        with patch(
            "openrouter_agent.gittools._project_has_own_git_repo", return_value=True
        ), patch(
            "openrouter_agent.gittools.subprocess.run",
            return_value=CompletedProcess(returncode=128, stderr="fatal: not a git repository (or any of the parent directories): .git"),
        ):
            result = gittools.git_status()
        self.assertEqual("Git command unavailable: this directory is not a git repository.", result)

    def test_run_git_reports_dubious_ownership_clearly(self):
        fake_root = gittools.config.ROOT / "workspace" / "beta"
        stderr = (
            "fatal: detected dubious ownership in repository at 'C:/repo/workspace/beta'\n"
            "To add an exception for this directory, call:\n\n"
            "        git config --global --add safe.directory C:/repo/workspace/beta"
        )
        with patch("openrouter_agent.gittools._project_has_own_git_repo", return_value=True), patch(
            "openrouter_agent.gittools.current_project_root", return_value=fake_root
        ), patch(
            "openrouter_agent.gittools.subprocess.run",
            return_value=CompletedProcess(returncode=128, stderr=stderr),
        ):
            result = gittools.git_status()
        self.assertIn("dubious ownership", result.lower())
        self.assertIn("git config --global --add safe.directory", result)
        self.assertIn(str(fake_root), result)

    def test_git_safe_directory_returns_command(self):
        fake_root = gittools.config.ROOT / "workspace" / "beta"
        with patch("openrouter_agent.gittools.current_project_root", return_value=fake_root):
            result = gittools.git_safe_directory()
        self.assertIn("git config --global --add safe.directory", result)
        self.assertIn(fake_root.as_posix(), result)

    def test_git_safe_directory_apply_runs_git_config(self):
        calls = []

        def fake_run(cmd, capture_output, text, timeout):
            calls.append(cmd)
            return CompletedProcess(stdout="")

        fake_root = gittools.config.ROOT / "workspace" / "beta"
        with patch("openrouter_agent.gittools.current_project_root", return_value=fake_root), patch(
            "openrouter_agent.gittools._confirm_git_action", return_value=True
        ), patch("openrouter_agent.gittools.subprocess.run", side_effect=fake_run):
            result = gittools.git_safe_directory(apply=True)

        self.assertIn(["git", "config", "--global", "--add", "safe.directory", fake_root.as_posix()], calls)
        self.assertEqual("Active project added to global git safe.directory.", result)

    def test_git_commit_only_stages_workspace(self):
        calls = []

        def fake_run(cmd, cwd, capture_output, text, timeout):
            calls.append(cmd)
            if cmd[1:3] == ["status", "--short"]:
                return CompletedProcess(stdout=" M example.py\n")
            if cmd[1] == "diff":
                return CompletedProcess(stdout="diff --git a/example.py b/example.py\n")
            return CompletedProcess(stdout="ok\n")

        with patch("openrouter_agent.gittools._project_has_own_git_repo", return_value=True), patch(
            "openrouter_agent.gittools.subprocess.run", side_effect=fake_run
        ), patch(
            "openrouter_agent.gittools._confirm_git_action", return_value=True
        ), patch("builtins.print") as mock_print:
            result = gittools.git_commit("test message")

        self.assertIn(["git", "add", "--", "."], calls)
        self.assertIn(["git", "commit", "-m", "test message"], calls)
        self.assertIn("ok", result)
        printed = "\n".join(" ".join(str(arg) for arg in call.args) for call in mock_print.call_args_list)
        self.assertIn("Project diff preview:", printed)
        self.assertIn("diff --git a/example.py b/example.py", printed)

    def test_git_commit_stops_when_diff_has_no_output(self):
        calls = []

        def fake_run(cmd, cwd, capture_output, text, timeout):
            calls.append(cmd)
            if cmd[1:3] == ["status", "--short"]:
                return CompletedProcess(stdout="?? example.py\n")
            if cmd[1] == "diff":
                return CompletedProcess(returncode=0, stdout="")
            return CompletedProcess(stdout="ok\n")

        with patch("openrouter_agent.gittools._project_has_own_git_repo", return_value=True), patch(
            "openrouter_agent.gittools.subprocess.run", side_effect=fake_run
        ), patch(
            "openrouter_agent.gittools._confirm_git_action", return_value=True
        ) as mock_confirm, patch("builtins.print") as mock_print:
            result = gittools.git_commit("test message")

        self.assertIn(["git", "add", "--", "."], calls)
        self.assertIn(["git", "commit", "-m", "test message"], calls)
        mock_confirm.assert_called_once()
        printed = "\n".join(" ".join(str(arg) for arg in call.args) for call in mock_print.call_args_list)
        self.assertIn("no tracked diff output; commit may contain untracked files", printed)
        self.assertIn("ok", result)

    def test_git_branch_cancelled_without_confirmation(self):
        with patch("openrouter_agent.gittools._confirm_git_action", return_value=False):
            result = gittools.git_branch("feature/test")
        self.assertEqual("Git action cancelled.", result)


if __name__ == "__main__":
    unittest.main()
