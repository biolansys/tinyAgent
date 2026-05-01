import subprocess
from . import config
from .project_context import current_project_root
from .results import OperationResult
from .tools.files import safe_path


def _git_safe_directory_path():
    return current_project_root().as_posix()


def git_safe_directory_command():
    return f"git config --global --add safe.directory {_git_safe_directory_path()}"


def _dubious_ownership_message(stderr):
    project_root = current_project_root()
    return (
        "Git blocked this repository because of dubious ownership.\n"
        f"Active project: {project_root}\n"
        "The project directory is owned by a different Windows user/SID than the current user.\n"
        "Fix it with:\n"
        f"{git_safe_directory_command()}\n\n"
        f"Git details:\n{stderr.strip()}"
    )


def _project_git_marker():
    return current_project_root() / ".git"


def _project_has_own_git_repo():
    return _project_git_marker().exists()


def _confirm_git_action(action):
    print(f"\nGit action requested: {action}\nWorking directory: {current_project_root()}")
    return input("Allow git action? [y/N]: ").strip().lower() == "y"


def _run_git_result(args, require_repo=True):
    if require_repo and not _project_has_own_git_repo():
        return OperationResult(
            False,
            "Git command unavailable: the active project is not initialized as its own git repository.",
            category="validation",
        )
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(current_project_root()),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if "not a git repository" in stderr.lower():
                return OperationResult(
                    False,
                    "Git command unavailable: this directory is not a git repository.",
                    code=result.returncode,
                    category="validation",
                )
            if "detected dubious ownership" in stderr.lower():
                return OperationResult(
                    False,
                    _dubious_ownership_message(stderr),
                    code=result.returncode,
                    category="validation",
                )
        out = (result.stdout or "") + (("\nSTDERR:\n" + result.stderr) if result.stderr else "")
        text = out.strip()
        if text:
            return OperationResult(result.returncode == 0, text, code=result.returncode, category="git")
        return OperationResult(
            result.returncode == 0,
            _empty_git_output_message(args, result.returncode),
            code=result.returncode,
            category="git",
        )
    except Exception as e:
        return OperationResult(False, f"Git command error: {e}", category="exception")


def _run_git(args, require_repo=True):
    return _run_git_result(args, require_repo=require_repo).text()


def _empty_git_output_message(args, returncode):
    if returncode != 0:
        return f"git {' '.join(args)} finished with code {returncode}"

    if args[:2] == ["status", "--short"]:
        return "Working tree clean."
    if args[:1] == ["diff"]:
        return "No diff output."
    if args[:1] == ["log"]:
        return "No commit history found."
    if args[:1] == ["show"]:
        return "No revision output."
    if args[:1] == ["restore"]:
        return "Restore completed."
    if args[:1] == ["add"]:
        return "Staging completed."
    if args[:1] == ["commit"]:
        return "Commit completed."
    if args[:1] == ["init"]:
        return "Git repository initialized."

    return f"git {' '.join(args)} finished with code {returncode}"


def git_status():
    return _run_git(["status", "--short", "--", "."])


def git_files():
    status = git_status()
    if status == "Working tree clean.":
        return "No changed files."
    return status


def git_diff():
    return _run_git(["diff", "--", "."])


def git_diff_cached():
    return _run_git(["diff", "--cached", "--", "."])


def git_log(limit=10):
    try:
        n = max(1, int(limit))
    except Exception:
        return "Invalid git log limit."
    return _run_git(["log", f"-n{n}", "--oneline", "--decorate"])


def git_show(ref="HEAD"):
    target = (ref or "HEAD").strip()
    if not target:
        target = "HEAD"
    return _run_git(["show", "--stat", "--oneline", target, "--"])


def git_commit_dry():
    status = git_status()
    if status == "Working tree clean.":
        return "No project changes to preview."
    diff = git_diff()
    if diff and diff != "No diff output.":
        preview = diff
    else:
        preview = "(no tracked diff output; changes may be untracked files)"
    return f"Project status:\n{status}\n\nProject diff preview:\n{preview}"


def git_add():
    status = git_status()
    if status == "Working tree clean.":
        return "No project changes to stage."
    if not _confirm_git_action("stage active project changes"):
        return "Git action cancelled."
    return _run_git(["add", "--", "."])


def git_unstage():
    status = git_status()
    if status == "Working tree clean.":
        return "No project changes to unstage."
    if not _confirm_git_action("unstage active project changes"):
        return "Git action cancelled."
    return _run_git(["restore", "--staged", "--", "."])


def git_branch(name):
    safe = "".join(c for c in name.strip() if c.isalnum() or c in "-_/.")
    if not safe:
        return "Invalid branch name."
    if not _confirm_git_action(f"create and switch to branch '{safe}'"):
        return "Git action cancelled."
    return _run_git(["checkout", "-b", safe])


def git_init():
    if _project_has_own_git_repo():
        return "Git repository already initialized."
    if not _confirm_git_action("initialize a git repository in the project root"):
        return "Git action cancelled."
    return _run_git(["init"], require_repo=False)


def git_commit(message):
    msg = message.strip().strip('"').strip("'")
    if not msg:
        return "Commit message is required."
    status = git_status()
    if status == "Working tree clean.":
        return "No project changes to commit."
    diff = git_diff()
    if diff and diff != "No diff output.":
        preview = diff
    else:
        preview = "(no tracked diff output; commit may contain untracked files)"
    print(f"\nProject diff preview:\n{preview}")
    if not _confirm_git_action(f"stage the active project and commit with message: {msg}"):
        return "Git action cancelled."
    add = _run_git(["add", "--", "."])
    commit = _run_git(["commit", "-m", msg])
    return f"{add}\n{commit}"


def _git_relative_path(path):
    resolved = safe_path(path)
    rel = resolved.relative_to(current_project_root())
    return str(rel).replace("\\", "/") or "."


def git_restore(path=""):
    target = (path or "").strip()
    status = git_status()
    if not status or status == "Working tree clean.":
        return "No project changes to restore."
    if target:
        rel = _git_relative_path(target)
        if not _confirm_git_action(f"restore tracked changes in file '{rel}'"):
            return "Git action cancelled."
        restore_staged = _run_git(["restore", "--staged", "--worktree", "--", rel])
        restore_worktree = _run_git(["restore", "--worktree", "--", rel])
        return f"{restore_staged}\n{restore_worktree}"
    if not _confirm_git_action("restore tracked changes in the active project"):
        return "Git action cancelled."
    restore_staged = _run_git(["restore", "--staged", "--worktree", "--", "."])
    restore_worktree = _run_git(["restore", "--worktree", "--", "."])
    return f"{restore_staged}\n{restore_worktree}"


def git_safe_directory(apply=False):
    command = git_safe_directory_command()
    if not apply:
        return (
            "To mark the active project as a safe Git directory, run:\n"
            f"{command}"
        )
    if not _confirm_git_action("mark the active project as a global git safe.directory"):
        return "Git action cancelled."
    try:
        result = subprocess.run(
            ["git", "config", "--global", "--add", "safe.directory", _git_safe_directory_path()],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            return stderr or f"git config finished with code {result.returncode}"
        return "Active project added to global git safe.directory."
    except Exception as e:
        return f"Git command error: {e}"
