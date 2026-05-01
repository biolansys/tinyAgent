import unittest
from pathlib import Path
from unittest.mock import patch

from openrouter_agent import memory
from openrouter_agent import audit


class MemoryHistoryTests(unittest.TestCase):
    def test_clear_memory_deletes_existing_file(self):
        mem_path = Path(r"C:\isolated\alpha\.agent_memory.json")

        def fake_exists(self):
            return self == mem_path

        with patch("openrouter_agent.memory.memory_file", return_value=mem_path), patch(
            "pathlib.Path.exists", autospec=True, side_effect=fake_exists
        ), patch("pathlib.Path.unlink", autospec=True) as mock_unlink:
            result = memory.clear_memory()

        self.assertEqual("Memory cleared.", result)
        mock_unlink.assert_called_once()

    def test_clear_history_deletes_existing_file(self):
        hist_path = Path(r"C:\isolated\logs\alpha\task_history.jsonl")

        def fake_exists(self):
            return self == hist_path

        with patch("openrouter_agent.audit.project_task_history_file", return_value=hist_path), patch(
            "pathlib.Path.exists", autospec=True, side_effect=fake_exists
        ), patch("pathlib.Path.unlink", autospec=True) as mock_unlink:
            result = audit.clear_history()

        self.assertEqual("Task history cleared.", result)
        mock_unlink.assert_called_once()


if __name__ == "__main__":
    unittest.main()
