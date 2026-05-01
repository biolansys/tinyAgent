import subprocess
import shlex
from pathlib import Path
from .. import config
from .files import read_text_file, safe_path
from ..project_context import current_project_root

SHELL_METACHARS = {"&", "|", ";", ">", "<", "`"}
ALLOWED_BINARIES = {"python", "python3", "py", "pip", "pip3", "pytest", "git", "dir", "ls", "type", "cat", "pwd"}


def _contains_shell_metacharacters(command):
    return any(ch in command for ch in SHELL_METACHARS) or "\n" in command or "\r" in command


def _parse_command(command, allowed_binaries=None):
    if _contains_shell_metacharacters(command):
        raise ValueError("Shell metacharacters are not allowed.")
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError as e:
        raise ValueError(f"Could not parse command: {e}") from e
    if not tokens:
        raise ValueError("Empty command.")
    tokens = [t[1:-1] if len(t) >= 2 and t[0] == t[-1] and t[0] in {"'", '"'} else t for t in tokens]
    binary = tokens[0].lower()
    allowed = {b.lower() for b in allowed_binaries} if allowed_binaries is not None else ALLOWED_BINARIES
    if binary not in allowed:
        raise ValueError("Command blocked. Only safe development commands are allowed.")
    return tokens


def _format_directory_listing(path: Path):
    if not path.exists():
        return f"Path does not exist: {path}"
    if not path.is_dir():
        return f"Not a directory: {path}"
    lines = []
    for item in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        rel = item.relative_to(config.WORKSPACE)
        prefix = "[DIR] " if item.is_dir() else "[FILE]"
        lines.append(f"{prefix} {rel}")
    return "\n".join(lines[:500]) or "Directory is empty."


def _handle_builtin(tokens):
    binary = tokens[0].lower()
    if binary in {"dir", "ls"}:
        if len(tokens) > 2:
            return "Usage: ls [PATH]"
        target = tokens[1] if len(tokens) > 1 else "."
        return _format_directory_listing(safe_path(target))
    if binary == "pwd":
        if len(tokens) != 1:
            return "Usage: pwd"
        return str(current_project_root())
    if binary in {"type", "cat"}:
        if len(tokens) != 2:
            return "Usage: cat PATH"
        return read_text_file(tokens[1])
    return None


def _validate_subprocess_tokens(tokens):
    binary = tokens[0].lower()
    if binary == "git":
        if len(tokens) < 2 or tokens[1].lower() not in {"status", "diff"}:
            raise ValueError("Only 'git status' and 'git diff' are allowed.")
    if binary in {"python", "python3", "py"} and len(tokens) > 1 and tokens[1] in {"-c", "/c", "-"}:
        raise ValueError("Inline Python execution is blocked.")


def run_shell_command(command, allowed_binaries=None):
    try:
        tokens = _parse_command(command.strip(), allowed_binaries=allowed_binaries)
        builtin_result = _handle_builtin(tokens)
        if builtin_result is not None:
            return builtin_result[:config.MAX_COMMAND_OUTPUT]
        _validate_subprocess_tokens(tokens)
    except Exception as e:
        return str(e)

    print(f"\nCommand requested:\n{' '.join(tokens)}\nWorking directory: {current_project_root()}")
    if input("Allow command? [y/N]: ").strip().lower() != "y":
        return "Command cancelled."

    try:
        r = subprocess.run(tokens, cwd=str(current_project_root()), capture_output=True, text=True, timeout=120, shell=False)
        out = (r.stdout or "") + (("\nSTDERR:\n" + r.stderr) if r.stderr else "")
        return out[:config.MAX_COMMAND_OUTPUT] or f"Command finished with code {r.returncode}"
    except Exception as e:
        return f"Command error: {e}"
