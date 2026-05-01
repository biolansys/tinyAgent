import unittest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from openrouter_agent import project_context
from openrouter_agent.tools import files


class ProjectIsolationTests(unittest.TestCase):
    def test_safe_path_stays_inside_active_project(self):
        project_root = Path(r"C:\isolated\alpha")
        with patch("openrouter_agent.tools.files.current_project_root", return_value=project_root), patch(
            "openrouter_agent.tools.files.get_active_project", return_value="alpha"
        ):
            inside = files.safe_path("src/app.py")
            self.assertEqual(project_root / "src" / "app.py", inside)
            with self.assertRaises(ValueError):
                files.safe_path("../beta/secrets.txt")

    def test_normalize_agent_path_strips_active_project_prefix(self):
        with patch("openrouter_agent.tools.files.get_active_project", return_value="alpha"):
            self.assertEqual("src/app.py", files.normalize_agent_path("workspace/alpha/src/app.py"))
            self.assertEqual("src/app.py", files.normalize_agent_path("alpha/src/app.py"))

    def test_project_context_creates_and_selects_projects(self):
        fake_workspace = Path(r"C:\isolated\workspace")
        fake_project_root = fake_workspace / "alpha"
        with patch("openrouter_agent.project_context.config.WORKSPACE", fake_workspace), patch(
            "openrouter_agent.project_context.Path.mkdir"
        ) as mock_mkdir, patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.is_dir", return_value=True
        ), patch("pathlib.Path.iterdir", return_value=[fake_project_root]):
            created = project_context.create_project("alpha")
            selected = project_context.set_active_project("alpha")
            self.assertEqual("alpha", created)
            self.assertEqual("alpha", selected)
            self.assertEqual("alpha", project_context.get_active_project())
            self.assertEqual(fake_project_root, project_context.current_project_root())
            self.assertEqual(["alpha"], project_context.list_projects())
            mock_mkdir.assert_called()

    def test_project_context_uses_saved_active_project(self):
        fake_workspace = Path(r"C:\isolated\workspace")
        fake_saved = fake_workspace / ".active_project.json"
        fake_project_root = fake_workspace / "beta"
        saved_json = json.dumps({"active_project": "beta"})

        def fake_exists(path_obj):
            return path_obj in {fake_saved, fake_project_root}

        with patch("openrouter_agent.project_context.ACTIVE_PROJECT_FILE", fake_saved), patch(
            "openrouter_agent.project_context.config.WORKSPACE", fake_workspace
        ), patch("pathlib.Path.exists", autospec=True, side_effect=fake_exists), patch(
            "pathlib.Path.is_dir", autospec=True, return_value=True
        ), patch("pathlib.Path.read_text", autospec=True, return_value=saved_json), patch(
            "openrouter_agent.project_context._active_project", None
        ):
            self.assertEqual("beta", project_context.get_active_project())

    def test_rename_project_updates_active_project(self):
        fake_workspace = Path(r"C:\isolated\workspace")
        old_root = fake_workspace / "alpha"
        new_root = fake_workspace / "beta"
        with patch("openrouter_agent.project_context.config.WORKSPACE", fake_workspace), patch(
            "pathlib.Path.exists", autospec=True, side_effect=lambda self: self == old_root
        ), patch("pathlib.Path.is_dir", autospec=True, return_value=True), patch(
            "pathlib.Path.rename", autospec=True
        ) as mock_rename, patch("openrouter_agent.project_context._save_active_project") as mock_save:
            project_context._active_project = "alpha"
            renamed = project_context.rename_project("alpha", "beta")
        self.assertEqual("beta", renamed)
        self.assertEqual("beta", project_context._active_project)
        mock_rename.assert_called_once()
        mock_save.assert_called_once_with("beta")

    def test_delete_project_clears_saved_active_when_last_project_removed(self):
        fake_workspace = Path(r"C:\isolated\workspace")
        alpha_root = fake_workspace / "alpha"
        with patch("openrouter_agent.project_context.config.WORKSPACE", fake_workspace), patch(
            "pathlib.Path.exists", autospec=True, side_effect=lambda self: self == alpha_root
        ), patch("pathlib.Path.is_dir", autospec=True, return_value=True), patch(
            "openrouter_agent.project_context.shutil.rmtree"
        ) as mock_rmtree, patch("openrouter_agent.project_context.list_projects", return_value=[]), patch(
            "openrouter_agent.project_context.clear_saved_active_project"
        ) as mock_clear:
            project_context._active_project = "alpha"
            deleted = project_context.delete_project("alpha")
        self.assertEqual("alpha", deleted)
        self.assertIsNone(project_context._active_project)
        mock_rmtree.assert_called_once()
        mock_clear.assert_called_once()



if __name__ == "__main__":
    unittest.main()
