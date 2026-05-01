import json
import uuid
from datetime import datetime
from .project_context import project_task_history_file, project_tool_audit_file, get_active_project


def _append_jsonl(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def new_task_id():
    return datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8]


def log_task_start(task_id, user_input):
    _append_jsonl(project_task_history_file(), {
        "type": "task_start",
        "task_id": task_id,
        "project": get_active_project(),
        "time": datetime.now().isoformat(timespec="seconds"),
        "user_input": user_input,
    })


def log_task_plan(task_id, plan):
    _append_jsonl(project_task_history_file(), {
        "type": "task_plan",
        "task_id": task_id,
        "project": get_active_project(),
        "time": datetime.now().isoformat(timespec="seconds"),
        "plan": plan,
    })


def log_task_end(task_id, result):
    _append_jsonl(project_task_history_file(), {
        "type": "task_end",
        "task_id": task_id,
        "project": get_active_project(),
        "time": datetime.now().isoformat(timespec="seconds"),
        "result_preview": str(result)[:4000],
    })


def log_tool_call(task_id, name, args, result):
    _append_jsonl(project_tool_audit_file(), {
        "type": "tool_call",
        "task_id": task_id,
        "project": get_active_project(),
        "time": datetime.now().isoformat(timespec="seconds"),
        "tool": name,
        "args": args,
        "result_preview": str(result)[:4000],
    })


def read_jsonl(path, limit=20):
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows = []
    for line in lines[-limit:]:
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def audit_report(limit=30):
    rows = read_jsonl(project_tool_audit_file(), limit=limit)
    if not rows:
        return "No tool audit entries found."

    out = ["Tool Audit", "=========="]
    for r in rows:
        out.append(
            f"{r.get('time')} | task={r.get('task_id')} | tool={r.get('tool')}\n"
            f"  args={json.dumps(r.get('args'), ensure_ascii=False)[:500]}\n"
            f"  result={r.get('result_preview', '')[:500]}"
        )
    return "\n".join(out)


def clear_audit():
    path = project_tool_audit_file()
    if path.exists():
        path.unlink()
    return "Tool audit cleared."


def history_report(limit=20):
    rows = read_jsonl(project_task_history_file(), limit=limit * 3)
    if not rows:
        return "No task history entries found."

    grouped = {}
    for r in rows:
        grouped.setdefault(r.get("task_id"), []).append(r)

    out = ["Task History", "============"]
    for task_id, events in list(grouped.items())[-limit:]:
        start = next((e for e in events if e.get("type") == "task_start"), {})
        end = next((e for e in reversed(events) if e.get("type") == "task_end"), {})
        out.append(
            f"{task_id} | {start.get('time', '-')}\n"
            f"  request={start.get('user_input', '-')[:500]}\n"
            f"  result={end.get('result_preview', '-')[:500]}"
        )
    return "\n".join(out)


def clear_history():
    path = project_task_history_file()
    if path.exists():
        path.unlink()
        return "Task history cleared."
    return "No task history entries found."


def task_detail(task_id):
    rows = read_jsonl(project_task_history_file(), limit=10000)
    matches = [r for r in rows if r.get("task_id") == task_id]
    if not matches:
        return f"No task found: {task_id}"
    return json.dumps(matches, indent=2, ensure_ascii=False)
