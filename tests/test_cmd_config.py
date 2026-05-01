import json
import unittest
from unittest.mock import patch

from openrouter_agent import config


class FakeCmdFile:
    def __init__(self, text=""):
        self.text = text

    def exists(self):
        return True

    def read_text(self, encoding="utf-8"):
        return self.text

    def write_text(self, text, encoding="utf-8"):
        self.text = text


class CmdConfigTests(unittest.TestCase):
    def test_load_cmd_commands_file_returns_empty_for_missing_file(self):
        class MissingCmdFile:
            def exists(self):
                return False

        self.assertEqual({}, config.load_cmd_commands_file(MissingCmdFile()))

    def test_add_cmd_command_updates_config_file(self):
        cmd_file = FakeCmdFile(json.dumps({"dir": "dir"}) + "\n")
        with patch("openrouter_agent.config.CMD_COMMANDS_FILE", cmd_file):
            saved = config.add_cmd_command("whoami", "whoami")
            data = json.loads(cmd_file.read_text(encoding="utf-8"))
        self.assertEqual("whoami", saved)
        self.assertEqual({"dir": "dir", "whoami": "whoami"}, data)

    def test_remove_cmd_command_updates_config_file(self):
        cmd_file = FakeCmdFile(json.dumps({"dir": "dir", "pwd": "pwd"}) + "\n")
        with patch("openrouter_agent.config.CMD_COMMANDS_FILE", cmd_file):
            removed = config.remove_cmd_command("pwd")
            data = json.loads(cmd_file.read_text(encoding="utf-8"))
        self.assertEqual("pwd", removed)
        self.assertEqual({"dir": "dir"}, data)

    def test_add_cmd_command_uses_explicit_target_file(self):
        cmd_file = FakeCmdFile(json.dumps({"dir": "dir"}) + "\n")
        saved = config.add_cmd_command("cat", "cat", path=cmd_file)
        data = json.loads(cmd_file.read_text(encoding="utf-8"))
        self.assertEqual("cat", saved)
        self.assertEqual({"cat": "cat", "dir": "dir"}, data)

    def test_remove_cmd_command_uses_explicit_target_file(self):
        cmd_file = FakeCmdFile(json.dumps({"dir": "dir", "cat": "cat"}) + "\n")
        removed = config.remove_cmd_command("cat", path=cmd_file)
        data = json.loads(cmd_file.read_text(encoding="utf-8"))
        self.assertEqual("cat", removed)
        self.assertEqual({"dir": "dir"}, data)

    def test_load_cmd_binaries_uses_configured_command_binaries(self):
        with patch("openrouter_agent.config.load_cmd_commands", return_value={"list": "dir", "show": "cat"}):
            binaries = config.load_cmd_binaries()
        self.assertEqual({"dir", "cat"}, binaries)


if __name__ == "__main__":
    unittest.main()
