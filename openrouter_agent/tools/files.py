import json, shutil, difflib, zipfile
from datetime import datetime
from .. import config
from ..project_context import current_project_root, get_active_project

def normalize_agent_path(path):
    if path is None:
        return ""
    path = str(path).strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    while path == "workspace" or path.startswith("workspace/"):
        if path == "workspace":
            path = ""
            break
        path = path[len("workspace/"):]
    active = get_active_project()
    if path == active:
        return ""
    if path.startswith(active + "/"):
        return path[len(active) + 1:]
    return path

def safe_path(path):
    root = current_project_root()
    p = (root / normalize_agent_path(path)).resolve()
    p.relative_to(root)
    return p

def is_ignored(path):
    return bool(set(path.parts).intersection(config.IGNORE_DIRS))

def backup(path):
    rel = path.relative_to(current_project_root())
    out = config.BACKUP_DIR / get_active_project() / rel
    out = out.with_name(f"{out.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, out)
    return out

def file_tree(path=".", max_depth=3):
    root = safe_path(path)
    if not root.exists():
        return f"Path does not exist: {path}"
    lines = []
    def walk(cur, depth):
        if depth > max_depth:
            return
        for item in sorted(cur.iterdir()):
            if is_ignored(item):
                continue
            rel = item.relative_to(root)
            pref = "  " * depth
            lines.append(f"{pref}[DIR]  {rel}" if item.is_dir() else f"{pref}[FILE] {rel}")
            if item.is_dir():
                walk(item, depth + 1)
    walk(root, 0)
    return "\n".join(lines[:1000]) or "No files found."

def read_text_file(path):
    p = safe_path(path)
    if is_ignored(p):
        return "Access denied. Ignored path."
    if not p.exists():
        return f"File does not exist: {path}"
    if p.stat().st_size > config.MAX_FILE_SIZE:
        return f"File too large. Limit is {config.MAX_FILE_SIZE} bytes."
    return p.read_text(encoding="utf-8", errors="replace")

def read_file_with_line_numbers(path, start_line=1, end_line=0):
    text = read_text_file(path)
    if text.startswith(("File does not", "Access denied", "File too large")):
        return text
    lines = text.splitlines()
    if end_line <= 0:
        end_line = len(lines)
    out = []
    for i in range(max(1, start_line), min(end_line, len(lines)) + 1):
        out.append(f"{i:5d}: {lines[i-1]}")
    return "\n".join(out)

def write_text_file(path, content):
    p = safe_path(path)
    if is_ignored(p):
        return "Write denied. Ignored path."
    msg = ""
    if p.exists():
        b = backup(p)
        msg = f" Backup: {b}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"File written: {p.relative_to(current_project_root())}.{msg}"

def replace_in_file(path, old_text, new_text):
    p = safe_path(path)
    original = read_text_file(path)
    if old_text not in original:
        return "Text to replace was not found."
    updated = original.replace(old_text, new_text, 1)
    diff = "\n".join(difflib.unified_diff(original.splitlines(), updated.splitlines(), lineterm=""))
    print(diff[:10000])
    if p.exists():
        backup(p)
    p.write_text(updated, encoding="utf-8")
    return f"File edited: {p.relative_to(current_project_root())}"

def patch_lines(path, start_line, end_line, new_text):
    p = safe_path(path)
    lines = read_text_file(path).splitlines()
    if start_line < 1 or end_line < start_line or end_line > len(lines):
        return f"Invalid range. File has {len(lines)} lines."
    new_lines = lines[:start_line-1] + new_text.splitlines() + lines[end_line:]
    if p.exists():
        backup(p)
    p.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return f"Patch applied: {p.relative_to(current_project_root())}"

def search_files(query, path=".", extensions=".py,.txt,.md,.json,.yaml,.yml,.html,.css,.js,.ts,.sql"):
    root = safe_path(path)
    exts = [x.strip().lower() for x in extensions.split(",") if x.strip()]
    results = []
    for f in root.rglob("*"):
        if is_ignored(f) or not f.is_file() or f.suffix.lower() not in exts:
            continue
        if f.stat().st_size > config.MAX_FILE_SIZE:
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if query.lower() in line.lower():
                results.append(f"{f.relative_to(root)}:{i}: {line.strip()}")
    return "\n".join(results[:300]) or "No matches found."

def snapshot(name=""):
    safe = "".join(c for c in (name or "workspace") if c.isalnum() or c in "-_")
    project_root = current_project_root()
    project_name = get_active_project()
    out = config.SNAPSHOT_DIR / f"{project_name}-{safe}-{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in project_root.rglob("*"):
            if f.is_file() and not is_ignored(f):
                z.write(f, f.relative_to(project_root))
    return f"Snapshot created: {out}"

def export_repo(name="openrouter-agent-v17"):
    safe = "".join(c for c in name if c.isalnum() or c in "-_") or get_active_project()
    out = config.SNAPSHOT_DIR / f"{safe}.zip"
    root = current_project_root()
    skip_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in root.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(root)
            if set(rel.parts).intersection(skip_dirs) or rel.suffix == ".zip":
                continue
            z.write(f, rel)
    return f"Repo export created: {out}"

def validate_path(path):
    p = safe_path(path)
    root = current_project_root()
    return f"Input: {path}\nNormalized: {normalize_agent_path(path) or '.'}\nResolved: {p}\nRelative: {p.relative_to(root) if p != root else '.'}"
