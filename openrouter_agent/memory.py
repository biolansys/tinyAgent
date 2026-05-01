import json
from datetime import datetime
from .project_context import project_memory_file


def memory_file():
    return project_memory_file()

def load_memory():
    path = memory_file()
    if not path.exists():
        return {"project_type": "unknown", "notes": [], "summary": "", "last_updated": None}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"project_type": "unknown", "notes": [], "summary": "", "last_updated": None}

def save_memory(memory):
    memory["last_updated"] = datetime.now().isoformat(timespec="seconds")
    memory_file().write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")

def remember(note, project_type=None):
    m = load_memory()
    if project_type:
        m["project_type"] = project_type
    m.setdefault("notes", []).append({"time": datetime.now().isoformat(timespec="seconds"), "note": note})
    save_memory(m)
    return "Memory saved."

def clear_memory():
    path = memory_file()
    if path.exists():
        path.unlink()
        return "Memory cleared."
    return "No memory file found."

def read_memory_text():
    return json.dumps(load_memory(), indent=2, ensure_ascii=False)
