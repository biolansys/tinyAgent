import unittest
from pathlib import Path
from unittest.mock import patch

from openrouter_agent import guidance


class GuidanceTests(unittest.TestCase):
    def test_load_guidance_includes_project_agents(self):
        fake_root = Path(r"C:\repo")
        fake_project_root = fake_root / "workspace" / "alpha"
        root_agents = fake_root / "AGENTS.md"
        project_agents = fake_project_root / "AGENTS.md"
        root_skill = fake_root / "SKILL" / "SKILLS.md"

        def fake_exists(path_obj):
            return path_obj in {root_agents, project_agents, root_skill}

        def fake_read_text(path_obj, encoding="utf-8", errors="replace"):
            mapping = {
                root_agents: "root rules",
                project_agents: "project rules",
                root_skill: "skill rules",
            }
            return mapping[path_obj]

        with patch("openrouter_agent.guidance.ROOT", fake_root), patch(
            "openrouter_agent.guidance.SKILL_DIR", fake_root / "SKILL"
        ), patch("openrouter_agent.guidance.current_project_root", return_value=fake_project_root), patch(
            "pathlib.Path.exists", autospec=True, side_effect=fake_exists
        ), patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text), patch(
            "pathlib.Path.mkdir"
        ), patch("pathlib.Path.rglob", return_value=[root_skill]):
            text = guidance.load_guidance()

        self.assertIn("## AGENTS.md", text)
        self.assertIn("root rules", text)
        self.assertIn("## workspace\\alpha\\AGENTS.md", text)
        self.assertIn("project rules", text)
        self.assertIn("skill rules", text)


if __name__ == "__main__":
    unittest.main()
