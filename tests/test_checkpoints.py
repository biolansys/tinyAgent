import unittest
from pathlib import Path
import shutil
from unittest.mock import patch

from openrouter_agent import checkpoints


class CheckpointTests(unittest.TestCase):
    def test_save_and_load_checkpoint(self):
        base = Path(r"C:\Varios\IA\TinyAgent\openrouter-agent-v21-production\workspace\_test_checkpoints")
        if base.exists():
            shutil.rmtree(base, ignore_errors=True)
        base.mkdir(parents=True, exist_ok=True)
        try:
            with patch("openrouter_agent.checkpoints.project_log_dir", return_value=base):
                checkpoints.save_checkpoint("run1", {"status": "in_progress", "next_step_index": 2})
                data = checkpoints.load_checkpoint("run1")
        finally:
            shutil.rmtree(base, ignore_errors=True)
        self.assertIsNotNone(data)
        self.assertEqual("run1", data["task_id"])
        self.assertEqual("in_progress", data["status"])
        self.assertEqual(2, data["next_step_index"])

    def test_list_delete_and_clear_checkpoints(self):
        base = Path(r"C:\Varios\IA\TinyAgent\openrouter-agent-v21-production\workspace\_test_checkpoints")
        if base.exists():
            shutil.rmtree(base, ignore_errors=True)
        base.mkdir(parents=True, exist_ok=True)
        try:
            with patch("openrouter_agent.checkpoints.project_log_dir", return_value=base):
                checkpoints.save_checkpoint("run1", {"status": "in_progress", "next_step_index": 1})
                checkpoints.save_checkpoint("run2", {"status": "completed", "next_step_index": 2})
                rows = checkpoints.list_checkpoints()
                self.assertEqual(2, len(rows))
                self.assertTrue(any(r["task_id"] == "run1" for r in rows))
                self.assertTrue(checkpoints.delete_checkpoint("run1"))
                self.assertFalse(checkpoints.delete_checkpoint("missing"))
                count = checkpoints.clear_checkpoints()
                self.assertEqual(1, count)
                self.assertEqual([], checkpoints.list_checkpoints())
        finally:
            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
