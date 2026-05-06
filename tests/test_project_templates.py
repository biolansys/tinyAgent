import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openrouter_agent import project_context


class ProjectTemplateTests(unittest.TestCase):
    def test_apply_api_template_creates_starter_files(self):
        temp_dir = Path(tempfile.mkdtemp(prefix="tpl-api-"))
        try:
            with patch("openrouter_agent.project_context.config.WORKSPACE", temp_dir), patch(
                "openrouter_agent.project_context.ACTIVE_PROJECT_FILE", temp_dir / ".active_project.json"
            ):
                project_context.create_project("demoapi")
                result = project_context.apply_project_template("demoapi", "api")
                root = temp_dir / "demoapi"
                self.assertIn("Template applied: api", result)
                self.assertTrue((root / "app.py").exists())
                self.assertTrue((root / "tests" / "test_api_smoke.py").exists())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_apply_tkinter_template_creates_starter_files(self):
        temp_dir = Path(tempfile.mkdtemp(prefix="tpl-tk-"))
        try:
            with patch("openrouter_agent.project_context.config.WORKSPACE", temp_dir), patch(
                "openrouter_agent.project_context.ACTIVE_PROJECT_FILE", temp_dir / ".active_project.json"
            ):
                project_context.create_project("demotk")
                result = project_context.apply_project_template("demotk", "tkinter")
                root = temp_dir / "demotk"
                self.assertIn("Template applied: tkinter", result)
                self.assertTrue((root / "tkinter_app.py").exists())
                self.assertTrue((root / "tk_specs" / "system_info.py").exists())
                self.assertTrue((root / "tests" / "test_system_info.py").exists())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
