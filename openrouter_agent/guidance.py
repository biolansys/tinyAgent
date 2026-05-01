from .config import ROOT, SKILL_DIR
from .project_context import get_active_project, current_project_root

SYSTEM_PROMPT = """
You are a local AI coding agent.

Rules:
- Work only inside the active project under workspace.
- File paths are relative to the active project root. Do not prefix paths with workspace/ or the project name.
- Inspect files before modifying them.
- Prefer small, safe changes.
- Create backups before edits.
- Ask before shell commands.
- Follow AGENTS.md and SKILL/**/SKILLS.md when available.
"""

def ensure_guidance_files():
    SKILL_DIR.mkdir(parents=True, exist_ok=True)


def _existing_guidance_files():
    files = []
    agents = ROOT / "AGENTS.md"
    project_agents = current_project_root() / "AGENTS.md"
    root_skill = SKILL_DIR / "SKILLS.md"
    if agents.exists():
        files.append(agents)
    if project_agents.exists():
        files.append(project_agents)
    if root_skill.exists():
        files.append(root_skill)
    for f in sorted(SKILL_DIR.rglob("SKILLS.md")):
        if f != root_skill:
            files.append(f)
    return files

def load_guidance(max_chars=24000):
    ensure_guidance_files()
    chunks = []
    for f in _existing_guidance_files():
        chunks.append(f"## {f.relative_to(ROOT)}\n\n" + f.read_text(encoding="utf-8", errors="replace"))
    if not chunks:
        chunks.append("## Guidance\n\nNo repository guidance files were found.")
    text = "\n\n---\n\n".join(chunks)
    if len(text) <= max_chars:
        return text
    suffix = "\n\n[guidance truncated]\n"
    return text[:max_chars - len(suffix)] + suffix

def build_system_prompt():
    project_info = (
        f"Active project: {get_active_project()}\n"
        f"Active project root: {current_project_root()}"
    )
    return SYSTEM_PROMPT + "\n\n" + project_info + "\n\nActive repository guidance:\n\n" + load_guidance()
