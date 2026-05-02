from pathlib import Path


def plugin_ping(args="", state=None, runtime=None):
    extra = f" {args}" if args else ""
    active = getattr(state, "active_project", "unknown")
    return f"plugin-ping ok | project={active}{extra}"


def on_project_created(context=None, plugin=""):
    data = dict(context or {})
    root = Path(str(data.get("project_root", "")).strip())
    if not root:
        return {"action": "continue"}
    readme = root / "README.md"
    if not readme.exists():
        project_name = str(data.get("project_name", root.name))
        readme.write_text(
            f"# {project_name}\n\nProject created with plugin scaffolding.\n",
            encoding="utf-8",
        )
        return {"action": "warn", "message": f"{plugin}: created README.md"}
    return {"action": "continue"}


def before_task(context=None, plugin=""):
    data = dict(context or {})
    text = str(data.get("user_input", "")).strip()
    if text.startswith("!"):
        return {"action": "mutate", "updates": {"user_input": text.lstrip('!').strip()}}
    return {"action": "continue"}


def after_task(context=None, plugin=""):
    return {"action": "continue"}
