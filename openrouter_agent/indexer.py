import ast
import json
from . import config
from .tools.files import safe_path, is_ignored, normalize_agent_path
from .project_context import project_index_file, current_project_root

INDEX_EXTENSIONS = {
    ".py", ".md", ".txt", ".json", ".yaml", ".yml",
    ".sql", ".html", ".css", ".js", ".ts", ".php",
}


def _extract_python_symbols(text):
    symbols = {"functions": [], "classes": [], "imports": []}

    try:
        tree = ast.parse(text)
    except Exception:
        return symbols

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols["functions"].append(node.name)
        elif isinstance(node, ast.ClassDef):
            symbols["classes"].append(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                symbols["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            symbols["imports"].append(mod)

    return symbols


def _summarize_text(text, max_chars=500):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    preview = " ".join(lines[:12])
    if len(preview) > max_chars:
        preview = preview[:max_chars] + "..."
    return preview


def build_code_index(path="."):
    root = safe_path(path)
    records = []

    for file in root.rglob("*"):
        if is_ignored(file) or not file.is_file():
            continue

        if file.suffix.lower() not in INDEX_EXTENSIONS:
            continue

        try:
            if file.stat().st_size > config.MAX_FILE_SIZE:
                continue

            text = file.read_text(encoding="utf-8", errors="replace")
            rel = str(file.relative_to(current_project_root()))

            record = {
                "path": rel,
                "extension": file.suffix.lower(),
                "size": file.stat().st_size,
                "lines": len(text.splitlines()),
                "summary": _summarize_text(text),
                "functions": [],
                "classes": [],
                "imports": [],
            }

            if file.suffix.lower() == ".py":
                symbols = _extract_python_symbols(text)
                record.update(symbols)

            records.append(record)

        except Exception:
            continue

    data = {
        "root": str(current_project_root()),
        "files": records,
        "count": len(records),
    }

    project_index_file().write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return f"Code index created: {project_index_file()} ({len(records)} files)"


def load_code_index():
    path = project_index_file()
    if not path.exists():
        return {"files": [], "count": 0}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"files": [], "count": 0}


def index_stats():
    data = load_code_index()
    files = data.get("files", [])
    by_ext = {}

    for f in files:
        by_ext[f.get("extension", "")] = by_ext.get(f.get("extension", ""), 0) + 1

    lines = [
        f"Index file: {project_index_file()}",
        f"Indexed files: {len(files)}",
        "",
        "By extension:",
    ]

    for ext, count in sorted(by_ext.items()):
        lines.append(f"- {ext or '[none]'}: {count}")

    return "\n".join(lines)


def search_code_index(query, limit=20):
    query_l = query.lower().strip()

    if not query_l:
        return "Empty search query."

    data = load_code_index()
    hits = []

    for f in data.get("files", []):
        haystack = " ".join([
            f.get("path", ""),
            f.get("summary", ""),
            " ".join(f.get("functions", [])),
            " ".join(f.get("classes", [])),
            " ".join(f.get("imports", [])),
        ]).lower()

        if query_l in haystack:
            hits.append(f)

    if not hits:
        return "No index matches found. Run /index first if the index is stale."

    out = []

    for f in hits[:limit]:
        symbols = []
        if f.get("classes"):
            symbols.append("classes=" + ",".join(f["classes"][:5]))
        if f.get("functions"):
            symbols.append("functions=" + ",".join(f["functions"][:5]))
        out.append(
            f"{f['path']} ({f['lines']} lines, {f['size']} bytes)\n"
            f"  {'; '.join(symbols) if symbols else f.get('summary', '')[:160]}"
        )

    return "\n".join(out)


def explain_index_file(path):
    norm = normalize_agent_path(path)
    data = load_code_index()

    for f in data.get("files", []):
        if f.get("path") == norm:
            return json.dumps(f, indent=2, ensure_ascii=False)

    return f"File not found in index: {norm}. Run /index first."
