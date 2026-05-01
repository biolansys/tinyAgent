import unittest
from pathlib import Path
from unittest.mock import patch

from openrouter_agent import project_context


class ProjectCloneTests(unittest.TestCase):
    def test_clone_project_copies_tree_and_sets_active_project(self):
        fake_workspace = Path(r"C:\isolated\workspace")
        source_root = fake_workspace / "alpha"
        target_root = fake_workspace / "beta"

        def fake_exists(self):
            return self == source_root

        with patch("openrouter_agent.project_context.config.WORKSPACE", fake_workspace), patch(
            "pathlib.Path.exists", autospec=True, side_effect=fake_exists
        ), patch("pathlib.Path.is_dir", autospec=True, return_value=True), patch(
            "openrouter_agent.project_context.shutil.copytree"
        ) as mock_copy, patch("openrouter_agent.project_context._save_active_project") as mock_save:
            cloned = project_context.clone_project("alpha", "beta")

        self.assertEqual("beta", cloned)
        self.assertEqual("beta", project_context._active_project)
        mock_copy.assert_called_once_with(source_root, target_root)
        mock_save.assert_called_once_with("beta")


if __name__ == "__main__":
    unittest.main()
