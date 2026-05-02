import json
import uuid
from datetime import datetime
from .checkpoints import load_checkpoint
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


def latest_task_id():
    rows = read_jsonl(project_task_history_file(), limit=10000)
    for row in reversed(rows):
        if row.get("type") == "task_start" and row.get("task_id"):
            return str(row.get("task_id")).strip() or None
    return None


def task_context(task_id=None, event_limit=5):
    task_id = str(task_id or "").strip() or latest_task_id()
    if not task_id:
        return None

    rows = read_jsonl(project_task_history_file(), limit=10000)
    matches = [r for r in rows if r.get("task_id") == task_id]
    if not matches:
        checkpoint = load_checkpoint(task_id)
        if not checkpoint:
            return None
        return {
            "task_id": task_id,
            "project": get_active_project(),
            "request": checkpoint.get("user_input", ""),
            "checkpoint": {
                "status": checkpoint.get("status"),
                "phase": checkpoint.get("phase"),
                "next_step_index": checkpoint.get("next_step_index"),
                "updated_at": checkpoint.get("updated_at"),
            },
            "events": [],
        }

    start = next((r for r in matches if r.get("type") == "task_start"), {})
    plan = next((r for r in matches if r.get("type") == "task_plan"), {})
    end = next((r for r in reversed(matches) if r.get("type") == "task_end"), {})
    checkpoint = load_checkpoint(task_id)
    recent_events = []
    for row in matches[-max(1, int(event_limit or 5)):]:
        recent_events.append({
            "type": row.get("type"),
            "time": row.get("time"),
            "summary": row.get("user_input") or row.get("plan") or row.get("result_preview") or row.get("phase"),
        })

    context = {
        "task_id": task_id,
        "project": start.get("project") or get_active_project(),
        "request": start.get("user_input", ""),
        "plan": plan.get("plan", ""),
        "result": end.get("result_preview", ""),
        "event_count": len(matches),
        "events": recent_events,
    }
    if checkpoint:
        context["checkpoint"] = {
            "status": checkpoint.get("status"),
            "phase": checkpoint.get("phase"),
            "next_step_index": checkpoint.get("next_step_index"),
            "updated_at": checkpoint.get("updated_at"),
            "plan": checkpoint.get("plan"),
        }
    return context
