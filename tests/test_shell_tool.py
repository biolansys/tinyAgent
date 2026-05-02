import unittest
from unittest.mock import patch

from openrouter_agent.tools import shell


class ShellToolTests(unittest.TestCase):
    def test_rejects_shell_metacharacters(self):
        result = shell.run_shell_command("python -m pytest && whoami")
        self.assertIn("Shell metacharacters are not allowed.", result)

    def test_rejects_inline_python(self):
        result = shell.run_shell_command('python -c "print(1)"')
        self.assertIn("Inline Python execution is blocked.", result)

    def test_allows_builtin_cat_without_prompting(self):
        with patch("openrouter_agent.tools.shell.read_text_file", return_value="hello") as mock_read:
            result = shell.run_shell_command("cat notes.txt")
        self.assertEqual("hello", result)
        mock_read.assert_called_once_with("notes.txt")

    def test_allows_builtin_pwd_without_prompting(self):
        with patch("openrouter_agent.tools.shell.current_project_root", return_value="C:/workspace/alpha"):
            result = shell.run_shell_command("pwd")
        self.assertEqual("C:/workspace/alpha", result)

    def test_allows_configured_binary_when_explicitly_passed(self):
        with patch("builtins.input") as mock_input, patch("builtins.print"), patch(
            "openrouter_agent.tools.shell.subprocess.run"
        ) as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "coder"
            mock_run.return_value.stderr = ""
            result = shell.run_shell_command("whoami", allowed_binaries={"whoami"})
        self.assertEqual("coder", result)
        mock_run.assert_called_once()
        mock_input.assert_not_called()

    def test_cancelled_subprocess_command(self):
        with patch("builtins.input", return_value="n"), patch("builtins.print"), patch(
            "openrouter_agent.tools.shell.subprocess.run"
        ) as mock_run:
            result = shell.run_shell_command("python -m pip install demo-package")
        self.assertEqual("Command cancelled.", result)
        mock_run.assert_not_called()

    def test_run_shell_command_result_returns_structured_validation_error(self):
        result = shell.run_shell_command_result("python -m pytest && whoami")
        self.assertFalse(result.ok)
        self.assertEqual("validation", result.category)
        self.assertIn("Shell metacharacters are not allowed.", result.message)

    def test_background_task_shell_confirmation_is_blocked_cleanly(self):
        with patch("openrouter_agent.tools.shell._interactive_confirmation_available", return_value=False):
            result = shell.run_shell_command_result("python -m pip install demo-package")
        self.assertFalse(result.ok)
        self.assertEqual("confirmation", result.category)
        self.assertIn("blocked while a background task is running", result.message)


if __name__ == "__main__":
    unittest.main()
