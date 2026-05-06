import ast
import re
import unittest
from pathlib import Path


def load_cli_commands():
    cli_path = Path("openrouter_agent/cli.py")
    source = cli_path.read_text(encoding="utf-8")
    module = ast.parse(source)
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "COMMANDS" and isinstance(node.value, ast.Dict):
                commands = []
                for key in node.value.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        commands.append(key.value.strip())
                return sorted(commands)
    return []


def load_reference_commands():
    ref_path = Path("COMMAND_REFERENCE.md")
    text = ref_path.read_text(encoding="utf-8")
    pattern = re.compile(r"^- `(/[^`]+)`\s*$", re.MULTILINE)
    commands = [m.group(1).strip() for m in pattern.finditer(text)]
    return sorted(commands)


class CommandReferenceConsistencyTests(unittest.TestCase):
    def test_every_cli_command_has_reference_entry(self):
        cli_commands = set(load_cli_commands())
        ref_commands = set(load_reference_commands())
        missing = sorted(cli_commands - ref_commands)
        self.assertEqual(
            [],
            missing,
            msg="Commands missing from COMMAND_REFERENCE.md:\n" + "\n".join(missing),
        )


if __name__ == "__main__":
    unittest.main()
