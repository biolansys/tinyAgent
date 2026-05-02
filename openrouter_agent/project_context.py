import json
import shutil
import subprocess
from pathlib import Path
from . import config

DEFAULT_PROJECT = "default"
_active_project = None
ACTIVE_PROJECT_FILE = config.WORKSPACE / ".active_project.json"


def sanitize_project_name(name: str) -> str:
    safe = "".join(c for c in (name or "").strip() if c.isalnum() or c in "-_")
    return safe


def list_projects():
    return sorted([p.name for p in config.WORKSPACE.iterdir() if p.is_dir()])


def _save_active_project(name: str):
    ACTIVE_PROJECT_FILE.write_text(json.dumps({"active_project": name}, indent=2), encoding="utf-8")


def _load_saved_active_project():
    if not ACTIVE_PROJECT_FILE.exists():
        return None
    try:
        data = json.loads(ACTIVE_PROJECT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None
    name = sanitize_project_name(data.get("active_project", ""))
    return name or None


def clear_saved_active_project():
    if ACTIVE_PROJECT_FILE.exists():
        ACTIVE_PROJECT_FILE.unlink()


def project_root(name: str) -> Path:
    safe = sanitize_project_name(name)
    if not safe:
        raise ValueError("Invalid project name.")
    return (config.WORKSPACE / safe).resolve()


def ensure_project(name: str) -> Path:
    root = project_root(name)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _initialize_new_project(root: Path) -> None:
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "init"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,
            check=False,
        )
    except Exception:
        # Keep project creation functional even when git is unavailable.
        pass


def get_active_project() -> str:
    global _active_project
    if _active_project:
        return _active_project
    saved = _load_saved_active_project()
    if saved:
        root = project_root(saved)
        if root.exists() and root.is_dir():
            _active_project = saved
            return _active_project
    projects = list_projects()
    if projects:
        _active_project = projects[0]
        _save_active_project(_active_project)
        return _active_project
    default_root = ensure_project(DEFAULT_PROJECT)
    if not (default_root / ".git").exists():
        _initialize_new_project(default_root)
    _active_project = DEFAULT_PROJECT
    _save_active_project(_active_project)
    return _active_project


def set_active_project(name: str) -> str:
    global _active_project
    root = project_root(name)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Project does not exist: {name}")
    _active_project = root.name
    _save_active_project(_active_project)
    return _active_project


def create_project(name: str) -> str:
    global _active_project
    root = project_root(name)
    is_new = not root.exists()
    root = ensure_project(name)
    if is_new:
        _initialize_new_project(root)
    _active_project = root.name
    _save_active_project(_active_project)
    return _active_project


def clone_project(source_name: str, target_name: str) -> str:
    global _active_project
    source_root = project_root(source_name)
    if not source_root.exists() or not source_root.is_dir():
        raise ValueError(f"Project does not exist: {source_name}")
    target_root = project_root(target_name)
    if target_root.exists():
        raise ValueError(f"Target project already exists: {target_name}")
    shutil.copytree(source_root, target_root)
    _active_project = target_root.name
    _save_active_project(_active_project)
    return _active_project


def rename_project(old_name: str, new_name: str) -> str:
    global _active_project
    old_root = project_root(old_name)
    if not old_root.exists() or not old_root.is_dir():
        raise ValueError(f"Project does not exist: {old_name}")
    new_root = project_root(new_name)
    if new_root.exists():
        raise ValueError(f"Target project already exists: {new_name}")
    old_root.rename(new_root)
    if get_active_project() == old_root.name:
        _active_project = new_root.name
        _save_active_project(_active_project)
    return new_root.name


def delete_project(name: str) -> str:
    global _active_project
    root = project_root(name)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Project does not exist: {name}")
    shutil.rmtree(root)
    if _active_project == root.name:
        _active_project = None
    projects = list_projects()
    if projects:
        _active_project = projects[0]
        _save_active_project(_active_project)
    else:
        clear_saved_active_project()
    return root.name


def current_project_root() -> Path:
    return ensure_project(get_active_project())


def project_memory_file() -> Path:
    return current_project_root() / ".agent_memory.json"


def project_session_file() -> Path:
    return current_project_root() / ".agent_session.json"


def project_cmd_commands_file() -> Path:
    return current_project_root() / ".cmd_commands.json"


def project_index_file() -> Path:
    return current_project_root() / ".code_index.json"


def project_log_dir() -> Path:
    path = config.LOG_DIR / get_active_project()
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_task_history_file() -> Path:
    return project_log_dir() / "task_history.jsonl"


def project_tool_audit_file() -> Path:
    return project_log_dir() / "tool_audit.jsonl"


def project_info(name: str | None = None) -> dict:
    project_name = sanitize_project_name(name) if name else get_active_project()
    if not project_name:
        raise ValueError("Invalid project name.")
    root = project_root(project_name)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Project does not exist: {project_name}")

    file_count = 0
    dir_count = 0
    total_bytes = 0
    for path in root.rglob("*"):
        if path.is_file():
            file_count += 1
            try:
                total_bytes += path.stat().st_size
            except Exception:
                pass
        elif path.is_dir():
            dir_count += 1

    return {
        "name": root.name,
        "path": str(root),
        "active": root.name == get_active_project(),
        "files": file_count,
        "dirs": dir_count,
        "bytes": total_bytes,
        "has_git": (root / ".git").exists(),
        "has_agents": (root / "AGENTS.md").exists(),
        "has_session": (root / ".agent_session.json").exists(),
    }
