import json
from datetime import datetime
from .project_context import project_log_dir


def _runs_dir():
    path = project_log_dir() / "runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def checkpoint_file(task_id):
    return _runs_dir() / f"{task_id}.json"


def save_checkpoint(task_id, data):
    payload = dict(data)
    payload["task_id"] = task_id
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    checkpoint_file(task_id).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return payload


def load_checkpoint(task_id):
    path = checkpoint_file(task_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_checkpoints():
    rows = []
    runs = _runs_dir()
    for path in sorted(runs.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows.append({
            "task_id": data.get("task_id", path.stem),
            "status": data.get("status", "unknown"),
            "phase": data.get("phase", ""),
            "updated_at": data.get("updated_at", ""),
            "next_step_index": data.get("next_step_index", 0),
        })
    return rows


def delete_checkpoint(task_id):
    path = checkpoint_file(task_id)
    if not path.exists():
        return False
    path.unlink()
    return True


def clear_checkpoints():
    count = 0
    for path in _runs_dir().glob("*.json"):
        try:
            path.unlink()
            count += 1
        except Exception:
            pass
    return count
