import subprocess
import shlex
import threading
from pathlib import Path
from .. import config
from ..results import OperationResult
from .files import read_text_file, safe_path
from ..project_context import current_project_root

SHELL_METACHARS = {"&", "|", ";", ">", "<", "`"}
ALLOWED_BINARIES = {"python", "python3", "py", "pip", "pip3", "pytest", "git", "dir", "ls", "type", "cat", "pwd"}
READ_ONLY_BINARIES = {"whoami", "hostname", "where", "echo", "ver", "date", "time", "pytest", "unittest"}
READ_ONLY_GIT_SUBCOMMANDS = {"status", "diff", "log", "show"}
SESSION_APPROVED_COMMANDS = set()


def _interactive_confirmation_available():
    return threading.current_thread() is threading.main_thread()


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
        if len(tokens) < 2 or tokens[1].lower() not in READ_ONLY_GIT_SUBCOMMANDS:
            raise ValueError("Only read-only git commands are allowed.")
    if binary in {"python", "python3", "py"} and len(tokens) > 1 and tokens[1] in {"-c", "/c", "-"}:
        raise ValueError("Inline Python execution is blocked.")


def _is_read_only_python_command(tokens):
    binary = tokens[0].lower()
    if binary not in {"python", "python3", "py"}:
        return False
    if len(tokens) >= 3 and tokens[1] == "-m" and tokens[2].lower() in {"pytest", "unittest"}:
        return True
    return False


def _requires_confirmation(tokens):
    binary = tokens[0].lower()
    if binary in {"dir", "ls", "pwd", "type", "cat"}:
        return False
    if binary in READ_ONLY_BINARIES:
        return False
    if binary == "git" and len(tokens) >= 2 and tokens[1].lower() in READ_ONLY_GIT_SUBCOMMANDS:
        return False
    if _is_read_only_python_command(tokens):
        return False
    return True


def _approval_key(tokens):
    return (str(current_project_root()), tuple(tokens))


def run_shell_command_result(command, allowed_binaries=None):
    try:
        tokens = _parse_command(command.strip(), allowed_binaries=allowed_binaries)
        builtin_result = _handle_builtin(tokens)
        if builtin_result is not None:
            return OperationResult(True, builtin_result[:config.MAX_COMMAND_OUTPUT], category="builtin")
        _validate_subprocess_tokens(tokens)
    except Exception as e:
        return OperationResult(False, str(e), category="validation")

    if _requires_confirmation(tokens):
        approval_key = _approval_key(tokens)
        if approval_key not in SESSION_APPROVED_COMMANDS:
            if not _interactive_confirmation_available():
                return OperationResult(
                    False,
                    "Confirmation-required shell command blocked while a background task is running. Re-run it directly from the CLI.",
                    category="confirmation",
                )

            print(f"\nCommand requested:\n{' '.join(tokens)}\nWorking directory: {current_project_root()}")
            if input("Allow command? [y/N]: ").strip().lower() != "y":
                return OperationResult(False, "Command cancelled.", category="cancelled")
            SESSION_APPROVED_COMMANDS.add(approval_key)

    try:
        r = subprocess.run(tokens, cwd=str(current_project_root()), capture_output=True, text=True, timeout=120, shell=False)
        out = (r.stdout or "") + (("\nSTDERR:\n" + r.stderr) if r.stderr else "")
        return OperationResult(
            r.returncode == 0,
            out[:config.MAX_COMMAND_OUTPUT] or f"Command finished with code {r.returncode}",
            code=r.returncode,
            category="subprocess",
        )
    except Exception as e:
        return OperationResult(False, f"Command error: {e}", category="exception")


def run_shell_command(command, allowed_binaries=None):
    return run_shell_command_result(command, allowed_binaries=allowed_binaries).text()
