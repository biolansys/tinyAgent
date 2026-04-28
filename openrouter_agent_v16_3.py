
# openrouter_agent_v9.py
import os, json, math, shutil, difflib, subprocess, urllib.request, urllib.error, zipfile, time
from pathlib import Path
from datetime import datetime, timedelta

# ============================================================
# Terminal colors
# ============================================================
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)

    def c_user(text): return Fore.CYAN + str(text) + Style.RESET_ALL
    def c_agent(text): return Fore.GREEN + str(text) + Style.RESET_ALL
    def c_step(text): return Fore.YELLOW + str(text) + Style.RESET_ALL
    def c_error(text): return Fore.RED + str(text) + Style.RESET_ALL
    def c_info(text): return Fore.MAGENTA + str(text) + Style.RESET_ALL
    def c_success(text): return Fore.LIGHTGREEN_EX + str(text) + Style.RESET_ALL
    def c_warning(text): return Fore.LIGHTYELLOW_EX + str(text) + Style.RESET_ALL

except Exception:
    # ANSI fallback. Works in most modern terminals.
    def _ansi(code, text): return f"\033[{code}m{text}\033[0m"
    def c_user(text): return _ansi("96", str(text))
    def c_agent(text): return _ansi("92", str(text))
    def c_step(text): return _ansi("93", str(text))
    def c_error(text): return _ansi("91", str(text))
    def c_info(text): return _ansi("95", str(text))
    def c_success(text): return _ansi("92", str(text))
    def c_warning(text): return _ansi("33", str(text))

def print_info(text=""):
    print(c_info(text))

def print_success(text=""):
    print(c_success(text))

def print_error(text=""):
    print(c_error(text))

def print_step(text=""):
    print(c_step(text))

def print_warning(text=""):
    print(c_warning(text))

def print_agent(text=""):
    print(c_agent(text))

# ============================================================
# Optional Rich dashboard
# ============================================================
RICH_AVAILABLE = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.columns import Columns
    from rich.align import Align
    from rich.text import Text
    from rich.rule import Rule
    from rich.box import ROUNDED, DOUBLE
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.syntax import Syntax

    console = Console()
    RICH_AVAILABLE = True

except Exception:
    console = None
    RICH_AVAILABLE = False


def rich_print(text="", style=None):
    if RICH_AVAILABLE:
        console.print(text, style=style)
    else:
        print(text)


def rich_rule(title=""):
    if RICH_AVAILABLE:
        console.print(Rule(title, style="cyan"))
    else:
        print(c_info("=" * 60))
        if title:
            print(c_info(title))


def rich_panel(text, title="", style="cyan"):
    if RICH_AVAILABLE:
        console.print(Panel(str(text), title=title, border_style=style, box=ROUNDED))
    else:
        print(c_info(f"[{title}]"))
        print(text)


def rich_code(code, language="python", title="Code"):
    if RICH_AVAILABLE:
        console.print(Panel(Syntax(str(code), language, line_numbers=True), title=title, border_style="green"))
    else:
        print(c_info(f"[{title}]"))
        print(code)


def print_dashboard():
    """
    Professional startup/status dashboard.
    Uses Rich if installed; falls back to simple colored text.
    """
    if not RICH_AVAILABLE:
        print_banner()
        print_info("Install rich for dashboard UI: python -m pip install rich")
        return

    title = Text("MULTI-PROVIDER AI CODING AGENT V16.3", style="bold cyan")
    subtitle = Text("OpenRouter + Hugging Face • Tools • Memory • Profiles • Skills", style="green")

    header = Panel(
        Align.center(Text.assemble(title, "\n", subtitle)),
        border_style="cyan",
        box=DOUBLE,
    )

    env_table = Table(title="Environment", box=ROUNDED, border_style="blue")
    env_table.add_column("Item", style="bold")
    env_table.add_column("Value")

    env_table.add_row("Workspace", str(WORKSPACE))
    env_table.add_row("Provider mode", PROVIDER_MODE)
    env_table.add_row("Active profile", ACTIVE_PROFILE)
    env_table.add_row("OpenRouter", "configured" if OPENROUTER_API_KEY else "missing")
    env_table.add_row("Hugging Face", "configured" if HF_TOKEN else "missing")
    env_table.add_row("Rich UI", "enabled")

    model_table = Table(title="Models", box=ROUNDED, border_style="magenta")
    model_table.add_column("Selected routes", style="bold")
    if MODELS:
        for route in MODELS[:8]:
            model_table.add_row(route)
        if len(MODELS) > 8:
            model_table.add_row(f"... plus {len(MODELS) - 8} more")
    else:
        model_table.add_row("No models selected yet")

    files_table = Table(title="Files", box=ROUNDED, border_style="green")
    files_table.add_column("Resource", style="bold")
    files_table.add_column("Path")
    files_table.add_row("Memory", str(MEMORY_FILE))
    files_table.add_row("Logs", str(LOG_DIR))
    files_table.add_row("Backups", str(BACKUP_DIR))
    files_table.add_row("Snapshots", str(SNAPSHOT_DIR))
    files_table.add_row("Skills", str(SKILL_DIR))

    console.print(header)
    console.print(Columns([env_table, model_table, files_table], equal=True, expand=True))
    console.print()


def print_status_dashboard():
    """
    Runtime status dashboard.
    """
    if not RICH_AVAILABLE:
        print(provider_health_dashboard())
        print(usage_report())
        return

    health = Table(title="Provider Health", box=ROUNDED, border_style="cyan")
    health.add_column("Provider", style="bold")
    health.add_column("Enabled")
    health.add_column("Candidates", justify="right")
    health.add_column("Chat OK", justify="right")
    health.add_column("Tools OK", justify="right")

    stats = MODEL_STATS or {}
    providers = stats.get("providers", {})

    for provider in ["openrouter", "huggingface"]:
        p = providers.get(provider, {})
        health.add_row(
            provider,
            str(p.get("enabled")),
            str(len(p.get("candidate_models", []))),
            str(len(p.get("working_chat_models", []))),
            str(len(p.get("working_tool_models", []))),
        )

    usage = Table(title="Usage", box=ROUNDED, border_style="yellow")
    usage.add_column("Metric", style="bold")
    usage.add_column("Value", justify="right")
    usage.add_row("Calls", str(USAGE_STATS.get("calls", 0)))
    usage.add_row("Prompt tokens", str(USAGE_STATS.get("prompt_tokens", 0)))
    usage.add_row("Completion tokens", str(USAGE_STATS.get("completion_tokens", 0)))
    usage.add_row("Total tokens", str(USAGE_STATS.get("total_tokens", 0)))

    profile = Table(title="Profile", box=ROUNDED, border_style="green")
    profile.add_column("Setting", style="bold")
    profile.add_column("Value")
    profile.add_row("Active profile", ACTIVE_PROFILE)
    profile.add_row("Provider mode", PROVIDER_MODE)
    profile.add_row("Max steps", str(MAX_STEPS_PER_TASK))
    profile.add_row("Tool iterations", str(MAX_TOOL_ITERATIONS_PER_STEP))
    profile.add_row("Temperature", str(current_temperature()))
    profile.add_row("Auto mode", str(AUTO_MODE))
    profile.add_row("Reviewer", str(REVIEW_ENABLED))
    profile.add_row("Auto rounds", str(AUTO_MAX_ROUNDS))

    console.print(Columns([health, usage, profile], equal=True, expand=True))


def print_models_table():
    if not RICH_AVAILABLE:
        print("\n".join(MODELS))
        return

    table = Table(title="Selected Provider Routes", box=ROUNDED, border_style="magenta")
    table.add_column("#", justify="right")
    table.add_column("Provider")
    table.add_column("Model route")

    for i, route in enumerate(MODELS, start=1):
        provider, model = parse_model_route(route)
        table.add_row(str(i), provider, model)

    console.print(table)


def print_help_dashboard():
    if not RICH_AVAILABLE:
        print_help()
        return

    table = Table(title="Commands", box=ROUNDED, border_style="cyan")
    table.add_column("Command", style="bold green")
    table.add_column("Description")

    commands = [
        ("/help", "Show classic help"),
        ("/dashboard", "Show Rich status dashboard"),
        ("/auto on|off", "Enable/disable autonomous fix loop"),
        ("/review on|off", "Enable/disable reviewer agent"),
        ("/autorounds N", "Set max autonomous fix rounds"),
        ("/models", "Show selected model routes"),
        ("/modelstats", "Show raw discovery stats"),
        ("/health", "Show provider health dashboard"),
        ("/usage", "Show token usage"),
        ("/provider MODE", "Set provider: auto/openrouter/huggingface"),
        ("/profiles", "List profiles"),
        ("/profile NAME", "Activate profile"),
        ("/tooliters N", "Set max tool iterations per step"),
        ("/hfmodels", "Show Hugging Face model config"),
        ("/addhfmodel MODEL", "Add Hugging Face model"),
        ("/discover", "Re-discover provider models"),
        ("/snapshot NAME", "Create workspace ZIP snapshot"),
        ("/exportrepo NAME", "Create GitHub-ready repo ZIP"),
        ("/guidance", "Show active AGENTS/SKILL guidance"),
        ("/colors", "Show color test"),
        ("/banner", "Show classic banner"),
        ("/exit", "Save and exit"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)

# ============================================================
# Init Banner
# ============================================================
def _banner_line(text: str, width: int = 54) -> str:
    text = str(text)
    if len(text) > width:
        text = text[: width - 3] + "..."
    return "║ " + text.ljust(width) + " ║"


def print_banner():
    title = "MULTI-PROVIDER AI CODING AGENT V16.3"
    provider_line = f"Provider Mode: {PROVIDER_MODE}"
    profile_line = f"Active Profile: {ACTIVE_PROFILE}"
    workspace_line = f"Workspace: {WORKSPACE.name}"
    features_line = "Tools • Memory • Profiles • Snapshots • Skills"
    providers_line = "Providers: OpenRouter + Hugging Face"

    print()
    print(c_success("╔" + "═" * 56 + "╗"))
    print(c_success(_banner_line(title.center(54))))
    print(c_success("╠" + "═" * 56 + "╣"))
    print(c_info(_banner_line(providers_line)))
    print(c_info(_banner_line(features_line)))
    print(c_info(_banner_line(provider_line)))
    print(c_info(_banner_line(profile_line)))
    print(c_info(_banner_line(workspace_line)))
    print(c_success("╚" + "═" * 56 + "╝"))
    print()


def startup_animation():
    for msg in ["Initializing providers", "Loading profiles", "Preparing workspace"]:
        print(c_info(msg + "..."))
        time.sleep(0.12)


API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS_URL = "https://openrouter.ai/api/v1/models"
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
APP_TITLE = "Multi-Provider Python Coding Agent V16.3"

WORKSPACE = Path("./workspace").resolve(); WORKSPACE.mkdir(exist_ok=True)
LOG_DIR = Path("./logs").resolve(); LOG_DIR.mkdir(exist_ok=True)
BACKUP_DIR = Path("./backups").resolve(); BACKUP_DIR.mkdir(exist_ok=True)
SNAPSHOT_DIR = Path("./snapshots").resolve(); SNAPSHOT_DIR.mkdir(exist_ok=True)
MEMORY_FILE = WORKSPACE / ".agent_memory.json"
SKILL_DIR = Path("./SKILL").resolve(); SKILL_DIR.mkdir(exist_ok=True)
MAX_GUIDANCE_CHARS = 24_000
MODEL_CACHE_FILE = Path("./.openrouter_models_cache.json").resolve()
PROVIDER_CONFIG_FILE = Path("./.agent_providers.json").resolve()
PROFILE_CONFIG_FILE = Path("./.agent_profiles.json").resolve()
ACTIVE_PROFILE = "coding"
PROVIDER_MODE = "auto"  # auto | openrouter | huggingface
USAGE_STATS = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "by_provider": {}, "by_route": {}}

DEFAULT_OPENROUTER_MODELS = ["openrouter/free"]
DEFAULT_HUGGINGFACE_MODELS = [
    "Qwen/Qwen3-Coder-480B-A35B-Instruct",
    "deepseek-ai/DeepSeek-V3-0324",
    "meta-llama/Llama-3.1-8B-Instruct",
]
DEFAULT_MODELS = ["openrouter::openrouter/free"]
MODELS = DEFAULT_MODELS.copy()
MODEL_STATS = {}

MAX_MODEL_CHECKS = 30
MODEL_CHECK_TIMEOUT = 30
MODEL_CACHE_TTL_HOURS = 12
MAX_FILE_SIZE = 300_000
MAX_COMMAND_OUTPUT = 25_000
MAX_STEPS_PER_TASK = 12
MAX_MESSAGES_BEFORE_SUMMARY = 30
MAX_TOOL_ITERATIONS_PER_STEP = 20
AUTO_MODE = True
AUTO_MAX_ROUNDS = 3
REVIEW_ENABLED = True
API_RETRY_ATTEMPTS = 3
API_RETRY_BASE_SECONDS = 1.5

IGNORE_DIRS = {".git","__pycache__",".venv","venv","node_modules","dist","build",".pytest_cache",".mypy_cache",".ruff_cache"}

SYSTEM_PROMPT = """
You are a local Python coding agent.
Rules:
- Work only inside the workspace folder.
- Inspect files before modifying them.
- Never invent file contents.
- Prefer small safe changes.
- Use tools when useful.
- Before editing files, explain what you are changing.
- Shell commands require user confirmation.
- After changing code, suggest or run a safe test.
- Follow local project guidance from AGENTS.md and SKILL/**/SKILLS.md when available.
- File tool paths are always relative to workspace. Never prefix paths with workspace/.
- Use app.py, src/main.py, etc. instead of workspace/app.py.
"""

PLANNER_PROMPT = """
Return only valid JSON:
{
  "goal": "short goal",
  "project_type": "python|fastapi|flask|tkinter|javascript|sql|unknown",
  "steps": [
    {"id": 1, "title": "Inspect project", "action": "inspect"},
    {"id": 2, "title": "Modify files", "action": "edit"},
    {"id": 3, "title": "Run or suggest test", "action": "test"}
  ],
  "risk_level": "low|medium|high"
}
"""


REVIEWER_PROMPT = """
You are a strict code reviewer for a local coding agent.

Review the execution result and decide whether more work is needed.

Return only valid JSON:
{
  "status": "pass|needs_fix",
  "summary": "short review summary",
  "issues": ["issue 1", "issue 2"],
  "recommended_next_prompt": "short prompt for the executor if status is needs_fix"
}
"""

FIXER_PROMPT = """
You are a fixer agent.

Your job is to propose the smallest safe follow-up task based on a reviewer report.
Return only valid JSON:
{
  "fix_goal": "short goal",
  "user_prompt": "prompt to send back into the execution loop"
}
"""

def load_api_key():
    key = os.getenv("OPENROUTER_API_KEY")
    if key: return key
    env = Path(".env")
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None

OPENROUTER_API_KEY = load_api_key()

def load_huggingface_token():
    key = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
    if key:
        return key

    env = Path(".env")
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("HF_TOKEN=") or line.startswith("HUGGINGFACE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None

def load_huggingface_model_list():
    raw = os.getenv("HF_MODELS")
    env = Path(".env")
    if not raw and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("HF_MODELS="):
                raw = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

    if not raw:
        return DEFAULT_HUGGINGFACE_MODELS.copy()

    return [x.strip() for x in raw.split(",") if x.strip()]

HF_TOKEN = load_huggingface_token()

def load_provider_config():
    if PROVIDER_CONFIG_FILE.exists():
        try:
            return json.loads(PROVIDER_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"huggingface_models": load_huggingface_model_list(), "provider_mode": "auto"}


def save_provider_config(config):
    PROVIDER_CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def get_huggingface_models():
    config = load_provider_config()
    models = config.get("huggingface_models") or load_huggingface_model_list()
    return list(dict.fromkeys(models))


def add_huggingface_model(model_id):
    config = load_provider_config()
    models = config.get("huggingface_models") or load_huggingface_model_list()
    if model_id not in models:
        models.append(model_id)
    config["huggingface_models"] = models
    save_provider_config(config)
    return f"Added Hugging Face model: {model_id}"


def remove_huggingface_model(model_id):
    config = load_provider_config()
    models = config.get("huggingface_models") or load_huggingface_model_list()
    models = [m for m in models if m != model_id]
    config["huggingface_models"] = models
    save_provider_config(config)
    return f"Removed Hugging Face model: {model_id}"


def set_provider_mode(mode):
    global PROVIDER_MODE
    mode = mode.strip().lower()
    if mode not in {"auto", "openrouter", "huggingface"}:
        return "Invalid provider. Use: auto, openrouter, or huggingface."
    PROVIDER_MODE = mode
    config = load_provider_config()
    config["provider_mode"] = mode
    save_provider_config(config)
    return f"Provider mode set to: {PROVIDER_MODE}"


def load_provider_mode():
    global PROVIDER_MODE
    config = load_provider_config()
    mode = config.get("provider_mode", "auto")
    if mode not in {"auto", "openrouter", "huggingface"}:
        mode = "auto"
    PROVIDER_MODE = mode
    return PROVIDER_MODE


# ============================================================
# Agent profiles
# ============================================================
DEFAULT_PROFILES = {
    "fast": {
        "description": "Prefer faster, fewer-step execution.",
        "provider_mode": "auto",
        "max_steps_per_task": 4,
        "max_tool_iterations_per_step": 10,
        "temperature": 0.1,
    },
    "coding": {
        "description": "Balanced default profile for coding.",
        "provider_mode": "auto",
        "max_steps_per_task": 8,
        "max_tool_iterations_per_step": 20,
        "temperature": 0.2,
    },
    "debug": {
        "description": "More tool iterations for debugging complex errors.",
        "provider_mode": "auto",
        "max_steps_per_task": 12,
        "max_tool_iterations_per_step": 35,
        "temperature": 0.1,
    },
    "safe": {
        "description": "Conservative profile with fewer tool iterations.",
        "provider_mode": "auto",
        "max_steps_per_task": 5,
        "max_tool_iterations_per_step": 12,
        "temperature": 0.0,
    },
    "huggingface": {
        "description": "Prefer Hugging Face provider only.",
        "provider_mode": "huggingface",
        "max_steps_per_task": 8,
        "max_tool_iterations_per_step": 20,
        "temperature": 0.2,
    },
    "openrouter": {
        "description": "Prefer OpenRouter provider only.",
        "provider_mode": "openrouter",
        "max_steps_per_task": 8,
        "max_tool_iterations_per_step": 20,
        "temperature": 0.2,
    },
}


def ensure_profiles_file():
    if not PROFILE_CONFIG_FILE.exists():
        PROFILE_CONFIG_FILE.write_text(
            json.dumps({"active": ACTIVE_PROFILE, "profiles": DEFAULT_PROFILES}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def load_profiles():
    ensure_profiles_file()
    try:
        data = json.loads(PROFILE_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {"active": ACTIVE_PROFILE, "profiles": DEFAULT_PROFILES}

    profiles = data.setdefault("profiles", {})
    for name, profile in DEFAULT_PROFILES.items():
        profiles.setdefault(name, profile)

    data.setdefault("active", ACTIVE_PROFILE)
    return data


def save_profiles(data):
    PROFILE_CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def list_profiles():
    data = load_profiles()
    active = data.get("active", ACTIVE_PROFILE)
    lines = ["Available profiles:"]
    for name, profile in sorted(data.get("profiles", {}).items()):
        marker = "*" if name == active else "-"
        lines.append(f"{marker} {name}: {profile.get('description', '')}")
        lines.append(f"    provider={profile.get('provider_mode')} steps={profile.get('max_steps_per_task')} tool_iters={profile.get('max_tool_iterations_per_step')} temp={profile.get('temperature')}")
    return "\n".join(lines)


def apply_profile(name):
    global ACTIVE_PROFILE, MAX_STEPS_PER_TASK, MAX_TOOL_ITERATIONS_PER_STEP, PROVIDER_MODE

    data = load_profiles()
    profiles = data.get("profiles", {})

    if name not in profiles:
        return f"Unknown profile: {name}\n\n{list_profiles()}"

    profile = profiles[name]
    ACTIVE_PROFILE = name
    data["active"] = name
    save_profiles(data)

    if "provider_mode" in profile:
        set_provider_mode(profile["provider_mode"])

    if "max_steps_per_task" in profile:
        MAX_STEPS_PER_TASK = int(profile["max_steps_per_task"])

    if "max_tool_iterations_per_step" in profile:
        MAX_TOOL_ITERATIONS_PER_STEP = int(profile["max_tool_iterations_per_step"])

    return f"Profile activated: {name}"


def current_temperature():
    data = load_profiles()
    profile = data.get("profiles", {}).get(data.get("active", ACTIVE_PROFILE), {})
    try:
        return float(profile.get("temperature", 0.2))
    except Exception:
        return 0.2


def set_tool_iterations(value):
    global MAX_TOOL_ITERATIONS_PER_STEP
    try:
        n = int(value)
    except Exception:
        return "Invalid number. Example: /tooliters 30"

    if n < 3:
        return "Minimum tool iterations is 3."
    if n > 100:
        return "Maximum tool iterations is 100."

    MAX_TOOL_ITERATIONS_PER_STEP = n
    return f"Max tool iterations per step set to: {MAX_TOOL_ITERATIONS_PER_STEP}"

def ensure_env_example():
    p = Path(".env.example")
    if not p.exists():
        p.write_text("OPENROUTER_API_KEY=your_api_key_here\nHF_TOKEN=your_huggingface_token_here\n# Optional: HF_MODELS=model1,model2\n", encoding="utf-8")


# ============================================================
# Agent guidance files: AGENTS.md + SKILL/**/SKILLS.md
# ============================================================
def default_agents_md() -> str:
    return """# AGENTS.md

This file provides local instructions for AI coding agents working in this repository.

## Project Goal

Build and maintain a lightweight local coding agent that uses OpenRouter models, safe workspace tools, project memory, backups, and controlled command execution.

## Core Rules

- Work only inside the `workspace/` directory unless explicitly changing repository configuration files.
- Inspect files before modifying them.
- Prefer small, reversible edits.
- Create backups before overwriting files.
- Use line-based patches when possible.
- Never invent file contents.
- Ask for confirmation before running shell commands.
- Do not run destructive commands.
- Keep generated files organized and documented.

## Important Directories

- `workspace/` — working project area controlled by the agent.
- `logs/` — saved conversation sessions.
- `backups/` — automatic backups before edits.
- `snapshots/` — workspace ZIP snapshots.
- `SKILL/` — reusable skill instructions for the agent.

## Recommended Workflow

1. Inspect the project.
2. Create a short plan.
3. Read relevant files.
4. Apply minimal edits.
5. Run or suggest a safe test.
6. Save useful context to memory.

## Safety

Allowed shell commands should be limited to development tasks such as:

- `python app.py`
- `python -m pytest`
- `python -m pip install -r requirements.txt`
- `git status`
- `git diff`

Avoid destructive operations such as delete, format, shutdown, registry edits, or system-wide changes.
"""


def default_root_skills_md() -> str:
    return """# SKILLS.md

This directory contains skill instructions used by the local OpenRouter coding agent.

## Available Skills

- `python/SKILLS.md` — Python coding, debugging, and testing workflow.
- `openrouter/SKILLS.md` — OpenRouter model usage and agent behavior.
- `safety/SKILLS.md` — workspace safety, backups, and command rules.

## General Agent Skill

When solving a task:

1. Understand the request.
2. Inspect files before changing them.
3. Make a short plan.
4. Apply the smallest safe change.
5. Show diffs before editing.
6. Backup files before modification.
7. Run a safe test when possible.
8. Record useful notes in memory.
"""


def default_python_skills_md() -> str:
    return """# Python Skill

Guidance for Python development tasks.

## Coding Style

- Prefer clear, simple Python.
- Use standard library when possible.
- Add helpful error handling.
- Keep functions small and testable.
- Avoid unnecessary dependencies.

## Debugging Workflow

1. Read the traceback carefully.
2. Identify the exact file and line.
3. Inspect the relevant code.
4. Apply a minimal fix.
5. Run a safe command such as:
   - `python script.py`
   - `python -m pytest`

## Dependency Workflow

If dependencies are needed:

1. Create or update `requirements.txt`.
2. Use:
   - `python -m pip install -r requirements.txt`

## GUI Notes

For Tkinter projects:

- Keep UI updates on the main thread.
- Avoid blocking the UI loop.
- Use `after()` for scheduled UI updates.
"""


def default_openrouter_skills_md() -> str:
    return """# OpenRouter Skill

Guidance for using OpenRouter in this coding agent.

## Model Selection

- Prefer free working models discovered at startup.
- Prefer tool-capable models for agent mode.
- Fall back to chat-only models if tool calls fail.
- Cache model discovery results to reduce startup requests.

## API Behavior

- Validate every response before reading `choices`.
- Handle `error` responses gracefully.
- Retry with another model if one fails.
- Use low temperature for coding tasks.

## Tool Calling

When tools are enabled:

- Use tools only when useful.
- Do not assume file contents.
- Read files before editing.
- Use patch tools for targeted edits.
"""


def default_safety_skills_md() -> str:
    return """# Safety Skill

Safety rules for local agent execution.

## File Safety

- Restrict file operations to the workspace.
- Ignore risky or noisy directories:
  - `.git`
  - `venv`
  - `.venv`
  - `node_modules`
  - `dist`
  - `build`
  - `__pycache__`

## Edit Safety

- Show diffs before edits.
- Create backups before overwriting.
- Prefer line-based patches.
- Create snapshots before large refactors.

## Command Safety

Only allow safe development commands such as:

- `python`
- `python -m pytest`
- `python -m pip`
- `git status`
- `git diff`
- `dir`
- `ls`

Block destructive or system-level commands.
"""


def write_if_missing(path: Path, content: str, overwrite: bool = False) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and not overwrite:
        return f"exists: {path}"

    path.write_text(content, encoding="utf-8")
    return f"written: {path}"


def create_agent_guidance_files(overwrite: bool = False) -> str:
    """
    Create AGENTS.md and SKILL/**/SKILLS.md guidance files.
    Existing files are preserved unless overwrite=True.
    """
    results = []

    results.append(write_if_missing(Path("./AGENTS.md").resolve(), default_agents_md(), overwrite))
    results.append(write_if_missing(SKILL_DIR / "SKILLS.md", default_root_skills_md(), overwrite))
    results.append(write_if_missing(SKILL_DIR / "python" / "SKILLS.md", default_python_skills_md(), overwrite))
    results.append(write_if_missing(SKILL_DIR / "openrouter" / "SKILLS.md", default_openrouter_skills_md(), overwrite))
    results.append(write_if_missing(SKILL_DIR / "safety" / "SKILLS.md", default_safety_skills_md(), overwrite))

    return "\n".join(results)


def list_agent_guidance_files() -> str:
    files = [Path("./AGENTS.md").resolve()]

    if SKILL_DIR.exists():
        files.extend(sorted(SKILL_DIR.rglob("SKILLS.md")))

    lines = []
    for f in files:
        if f.exists():
            lines.append(str(f.relative_to(Path(".").resolve())))
        else:
            lines.append(f"missing: {f}")

    return "\n".join(lines) or "No guidance files found."


def load_agent_guidance(max_chars: int = MAX_GUIDANCE_CHARS) -> str:
    """
    Load AGENTS.md and SKILL/**/SKILLS.md into the active system prompt.
    """
    root = Path(".").resolve()
    chunks = []

    agents = root / "AGENTS.md"
    if agents.exists():
        try:
            content = agents.read_text(encoding="utf-8", errors="replace").strip()
            if content:
                chunks.append(f"## AGENTS.md\n\n{content}")
        except Exception as e:
            chunks.append(f"## AGENTS.md\n\nCould not read AGENTS.md: {e}")

    if SKILL_DIR.exists():
        for skill_file in sorted(SKILL_DIR.rglob("SKILLS.md")):
            try:
                rel = skill_file.relative_to(root)
            except Exception:
                rel = skill_file

            try:
                content = skill_file.read_text(encoding="utf-8", errors="replace").strip()
                if content:
                    chunks.append(f"## {rel}\n\n{content}")
            except Exception as e:
                chunks.append(f"## {rel}\n\nCould not read skill file: {e}")

    guidance = "\n\n---\n\n".join(chunks).strip()

    if not guidance:
        return ""

    if len(guidance) > max_chars:
        guidance = guidance[:max_chars] + "\n\n[TRUNCATED: guidance exceeded MAX_GUIDANCE_CHARS]"

    return guidance


def build_system_prompt() -> str:
    guidance = load_agent_guidance()

    if not guidance:
        return SYSTEM_PROMPT

    return (
        SYSTEM_PROMPT
        + "\n\n"
        + "The following repository guidance files are active instructions. "
          "Follow them unless they conflict with higher-priority safety rules.\n\n"
        + guidance
    )


def refresh_system_message(messages: list) -> list:
    new_system = {"role": "system", "content": build_system_prompt()}

    if not messages:
        return [new_system]

    if messages[0].get("role") == "system":
        messages[0] = new_system
        return messages

    return [new_system] + messages

def parse_model_route(route):
    """
    Model route format:
      openrouter::model-id
      huggingface::model-id
    Backward compatibility:
      plain model id => openrouter::model-id
      hf:model-id    => huggingface::model-id
    """
    if "::" in route:
        provider, model = route.split("::", 1)
        return provider.strip().lower(), model.strip()

    if route.startswith("hf:"):
        return "huggingface", route[3:].strip()

    return "openrouter", route.strip()


def make_model_route(provider, model):
    return f"{provider}::{model}"


def provider_display_name(route):
    provider, model = parse_model_route(route)
    return f"{provider}::{model}"


def headers(provider="openrouter", title=APP_TITLE):
    provider = provider.lower()

    if provider == "huggingface":
        if not HF_TOKEN:
            raise RuntimeError("Missing HF_TOKEN or HUGGINGFACE_API_KEY for Hugging Face provider.")
        return {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": APP_TITLE,
        }

    if not OPENROUTER_API_KEY:
        raise RuntimeError("Missing OPENROUTER_API_KEY for OpenRouter provider.")

    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": title,
    }


def provider_chat_url(provider):
    provider = provider.lower()

    if provider == "huggingface":
        return HF_API_URL

    return API_URL


def http_get_json(url, provider="openrouter", timeout=60):
    req = urllib.request.Request(
        url,
        method="GET",
        headers=headers(provider, "Model Discovery"),
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def http_post_json(url, payload, provider="openrouter", timeout=90):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers=headers(provider),
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


# ---------------- Multi-provider model discovery ----------------
def is_free_model(model):
    model_id = model.get("id", "")
    if model_id.endswith(":free"):
        return True
    pricing = model.get("pricing", {}) or {}
    zero = {"0", "0.0", "0.000000", "0.0000000", "0.00000000"}
    return str(pricing.get("prompt", "")) in zero and str(pricing.get("completion", "")) in zero


def fetch_openrouter_free_models():
    data = http_get_json(MODELS_URL, provider="openrouter")
    models = []
    for m in data.get("data", []):
        mid = m.get("id")
        if mid and is_free_model(m):
            models.append(mid)

    priority = ["coder", "code", "instruct", "chat", "qwen", "deepseek", "llama", "mistral", "gemma"]
    models.sort(key=lambda x: (not any(w in x.lower() for w in priority), x))
    return models


def fetch_huggingface_candidate_models():
    """
    Hugging Face does not expose the same free-model discovery API as OpenRouter here.
    This app uses HF_MODELS from .env or a small curated default list, then tests each model.
    """
    return get_huggingface_models()


def test_chat_route(route):
    provider, model = parse_model_route(route)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply only with OK."}],
        "temperature": 0,
        "max_tokens": 8,
    }

    try:
        data = http_post_json(
            provider_chat_url(provider),
            payload,
            provider=provider,
            timeout=MODEL_CHECK_TIMEOUT,
        )
        return "error" not in data and bool(data.get("choices"))
    except Exception:
        return False


def test_tools_route(route):
    provider, model = parse_model_route(route)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Use dummy_tool with value OK."}],
        "temperature": 0,
        "max_tokens": 80,
        "tools": [{
            "type": "function",
            "function": {
                "name": "dummy_tool",
                "description": "Return OK.",
                "parameters": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"]
                }
            }
        }],
        "tool_choice": "auto"
    }

    try:
        data = http_post_json(
            provider_chat_url(provider),
            payload,
            provider=provider,
            timeout=MODEL_CHECK_TIMEOUT,
        )
        if "error" in data or not data.get("choices"):
            return False
        msg = data["choices"][0].get("message", {})
        return bool(msg.get("tool_calls"))
    except Exception:
        return False


def load_model_cache():
    if not MODEL_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(MODEL_CACHE_FILE.read_text(encoding="utf-8"))
        last = datetime.fromisoformat(data["last_checked"])
        if datetime.now() - last < timedelta(hours=MODEL_CACHE_TTL_HOURS):
            return data
    except Exception:
        return None
    return None


def save_model_cache(stats):
    MODEL_CACHE_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")


def discover_models(force=False):
    global MODEL_STATS

    if not force:
        cached = load_model_cache()
        if cached:
            cached["loaded_from_cache"] = True
            MODEL_STATS = cached
            print("Loaded model discovery from cache.")
            return cached.get("selected_models") or DEFAULT_MODELS

    stats = {
        "last_checked": datetime.now().isoformat(timespec="seconds"),
        "loaded_from_cache": False,
        "providers": {
            "openrouter": {
                "enabled": bool(OPENROUTER_API_KEY),
                "candidate_models": [],
                "working_chat_models": [],
                "working_tool_models": [],
            },
            "huggingface": {
                "enabled": bool(HF_TOKEN),
                "candidate_models": [],
                "working_chat_models": [],
                "working_tool_models": [],
            },
        },
        "selected_models": [],
    }

    routes = []

    if OPENROUTER_API_KEY:
        print("Checking OpenRouter free models...")
        try:
            openrouter_models = fetch_openrouter_free_models()
        except Exception as e:
            print(f"Could not fetch OpenRouter models: {e}")
            openrouter_models = []

        stats["providers"]["openrouter"]["candidate_models"] = openrouter_models
        routes.extend(make_model_route("openrouter", m) for m in openrouter_models[:MAX_MODEL_CHECKS])
    else:
        print_warning("OPENROUTER_API_KEY not found. OpenRouter discovery skipped.")

    if HF_TOKEN:
        print("Checking Hugging Face candidate models...")
        hf_models = fetch_huggingface_candidate_models()
        stats["providers"]["huggingface"]["candidate_models"] = hf_models
        routes.extend(make_model_route("huggingface", m) for m in hf_models[:MAX_MODEL_CHECKS])
    else:
        print_warning("HF_TOKEN not found. Hugging Face provider skipped.")

    if not routes:
        print("No provider credentials found. Using default OpenRouter router as placeholder.")
        stats["selected_models"] = DEFAULT_MODELS.copy()
        MODEL_STATS = stats
        save_model_cache(stats)
        return stats["selected_models"]

    tool_routes = []
    chat_routes = []

    for route in routes:
        provider, model = parse_model_route(route)
        print(f"Testing: {route}")

        if test_chat_route(route):
            print("  CHAT OK")
            chat_routes.append(route)
            stats["providers"][provider]["working_chat_models"].append(model)

            if test_tools_route(route):
                print("  TOOLS OK")
                tool_routes.append(route)
                stats["providers"][provider]["working_tool_models"].append(model)
            else:
                print("  TOOLS FAILED")
        else:
            print("  CHAT FAILED")

    selected = tool_routes or chat_routes

    if not selected:
        selected = DEFAULT_MODELS.copy()

    stats["selected_models"] = selected
    MODEL_STATS = stats
    save_model_cache(stats)
    return selected


def clear_model_cache():
    if MODEL_CACHE_FILE.exists():
        MODEL_CACHE_FILE.unlink()
        return "Model cache cleared."
    return "No model cache found."

# ---------------- Safety/memory ----------------
def normalize_agent_path(path: str) -> str:
    """
    Normalize paths produced by the model.

    Tools already operate inside WORKSPACE, so paths like:
      workspace/app.py
      ./workspace/app.py
      workspace\\app.py

    are normalized to:
      app.py

    This prevents accidental workspace/workspace nesting.
    """
    if path is None:
        return ""

    path = str(path).strip().replace("\\", "/")

    while path.startswith("./"):
        path = path[2:]

    # Remove repeated workspace prefixes.
    while path == "workspace" or path.startswith("workspace/"):
        if path == "workspace":
            path = ""
            break
        path = path[len("workspace/"):]

    while path.startswith("./"):
        path = path[2:]

    return path


def safe_path(path):
    normalized = normalize_agent_path(path)
    p = (WORKSPACE / normalized).resolve()
    p.relative_to(WORKSPACE)
    return p

def is_ignored(path):
    return bool(set(path.parts).intersection(IGNORE_DIRS))

def make_backup(path):
    rel = path.relative_to(WORKSPACE)
    backup = BACKUP_DIR / rel
    backup = backup.with_name(f"{backup.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    return backup

def load_memory():
    if not MEMORY_FILE.exists():
        return {"project_type": "unknown", "notes": [], "summary": "", "last_updated": None}
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"project_type": "unknown", "notes": [], "summary": "", "last_updated": None}

def save_memory(memory):
    memory["last_updated"] = datetime.now().isoformat(timespec="seconds")
    MEMORY_FILE.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")
    return "Memory saved."

def remember_note(note, project_type=""):
    m = load_memory()
    if project_type: m["project_type"] = project_type
    m.setdefault("notes", []).append({"time": datetime.now().isoformat(timespec="seconds"), "note": note})
    return save_memory(m)

def read_memory():
    return json.dumps(load_memory(), indent=2, ensure_ascii=False)

# ---------------- Tools ----------------
def calculator(expression):
    allowed = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
               "pi": math.pi, "e": math.e, "abs": abs, "round": round, "min": min, "max": max}
    try:
        return str(eval(expression, {"__builtins__": {}}, allowed))
    except Exception as e:
        return f"Calculator error: {e}"

def file_tree(path=".", max_depth=3):
    try:
        root = safe_path(path)
        if not root.exists(): return f"Path does not exist: {path}"
        if not root.is_dir(): return f"Not a directory: {path}"
        lines = []
        def walk(cur, depth):
            if depth > max_depth: return
            for item in sorted(cur.iterdir()):
                if is_ignored(item): continue
                rel = item.relative_to(WORKSPACE)
                indent = "  " * depth
                if item.is_dir():
                    lines.append(f"{indent}[DIR]  {rel}")
                    walk(item, depth + 1)
                else:
                    lines.append(f"{indent}[FILE] {rel}")
        walk(root, 0)
        return "\n".join(lines[:1000]) or "No files found."
    except Exception as e:
        return f"File tree error: {e}"

def search_files(query, path=".", extensions=".py,.txt,.md,.json,.yaml,.yml,.html,.css,.js,.ts,.sql"):
    try:
        root = safe_path(path)
        exts = [x.strip().lower() for x in extensions.split(",") if x.strip()]
        results = []
        for file in root.rglob("*"):
            if is_ignored(file) or not file.is_file(): continue
            if file.suffix.lower() not in exts: continue
            if file.stat().st_size > MAX_FILE_SIZE: continue
            text = file.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(text.splitlines(), start=1):
                if query.lower() in line.lower():
                    results.append(f"{file.relative_to(WORKSPACE)}:{i}: {line.strip()}")
        return "\n".join(results[:300]) or "No matches found."
    except Exception as e:
        return f"Search error: {e}"

def read_text_file(path):
    try:
        p = safe_path(path)
        if is_ignored(p): return "Access denied. Ignored path."
        if not p.exists(): return f"File does not exist: {path}"
        if not p.is_file(): return f"Not a file: {path}"
        if p.stat().st_size > MAX_FILE_SIZE: return f"File too large. Limit is {MAX_FILE_SIZE} bytes."
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Read file error: {e}"

def write_text_file(path, content):
    try:
        p = safe_path(path)
        if is_ignored(p): return "Write denied. Ignored path."
        backup_msg = ""
        if p.exists():
            print(f"\nFile already exists: {p.relative_to(WORKSPACE)}")
            if input("Overwrite file? [y/N]: ").strip().lower() != "y":
                return "Write cancelled."
            backup_msg = f" | Backup: {make_backup(p)}"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"File written: {p.relative_to(WORKSPACE)}{backup_msg}"
    except Exception as e:
        return f"Write error: {e}"

def append_text_file(path, content):
    try:
        p = safe_path(path)
        if is_ignored(p): return "Append denied. Ignored path."
        backup_msg = f" | Backup: {make_backup(p)}" if p.exists() else ""
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f: f.write(content)
        return f"Text appended: {p.relative_to(WORKSPACE)}{backup_msg}"
    except Exception as e:
        return f"Append error: {e}"

def replace_in_file(path, old_text, new_text):
    try:
        p = safe_path(path)
        if is_ignored(p): return "Edit denied. Ignored path."
        if not p.exists(): return f"File does not exist: {path}"
        original = p.read_text(encoding="utf-8", errors="replace")
        if old_text not in original: return "Text to replace was not found."
        updated = original.replace(old_text, new_text, 1)
        diff = "\n".join(difflib.unified_diff(original.splitlines(), updated.splitlines(),
                                              fromfile=f"{path} original", tofile=f"{path} updated", lineterm=""))
        print_info("\nProposed diff:")
        print(diff[:10_000])
        if input("\nApply this edit? [y/N]: ").strip().lower() != "y": return "Edit cancelled."
        backup = make_backup(p)
        p.write_text(updated, encoding="utf-8")
        return f"File edited: {p.relative_to(WORKSPACE)} | Backup: {backup}"
    except Exception as e:
        return f"Replace error: {e}"

def patch_lines(path, start_line, end_line, new_text):
    try:
        p = safe_path(path)
        if is_ignored(p): return "Patch denied. Ignored path."
        if not p.exists(): return f"File does not exist: {path}"
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        if start_line < 1 or end_line < start_line or end_line > len(lines):
            return f"Invalid line range. File has {len(lines)} lines."
        updated_lines = lines[:start_line-1] + new_text.splitlines() + lines[end_line:]
        original = "\n".join(lines) + "\n"; updated = "\n".join(updated_lines) + "\n"
        diff = "\n".join(difflib.unified_diff(original.splitlines(), updated.splitlines(),
                                              fromfile=f"{path} original", tofile=f"{path} patched", lineterm=""))
        print_info("\nProposed patch:")
        print(diff[:10_000])
        if input("\nApply patch? [y/N]: ").strip().lower() != "y": return "Patch cancelled."
        backup = make_backup(p)
        p.write_text(updated, encoding="utf-8")
        return f"Patch applied: {p.relative_to(WORKSPACE)} | Backup: {backup}"
    except Exception as e:
        return f"Patch error: {e}"

def create_requirements(packages):
    lines = [p.strip() for p in packages.split(",") if p.strip()]
    if not lines: return "No packages provided."
    return write_text_file("requirements.txt", "\n".join(lines) + "\n")

def inspect_project():
    tree = file_tree(".", max_depth=2)
    indicators = {
        "requirements.txt": "python", "pyproject.toml": "python", "setup.py": "python",
        "app.py": "python", "main.py": "python", "manage.py": "python",
        "package.json": "javascript", "schema.sql": "sql",
    }
    found, project_type = [], "unknown"
    for name, kind in indicators.items():
        if (WORKSPACE / name).exists():
            found.append(name); project_type = kind
    remember_note(f"Project inspection found files: {found}", project_type=project_type)
    return f"Detected project type: {project_type}\nImportant files: {found}\n\nFile tree:\n{tree}"

def suggest_test_command(project_type="unknown"):
    if project_type in {"python", "tkinter", "fastapi", "flask", "unknown"}:
        if (WORKSPACE / "pytest.ini").exists() or (WORKSPACE / "tests").exists(): return "python -m pytest"
        if (WORKSPACE / "main.py").exists(): return "python main.py"
        if (WORKSPACE / "app.py").exists(): return "python app.py"
        return "python --version"
    if project_type == "javascript":
        if (WORKSPACE / "package.json").exists(): return "npm test"
        return "node --version"
    return "python --version"

def run_shell_command(command):
    allowed = ["python ","python3 ","py ","pip ","pip3 ","python -m pip ","py -m pip ",
               "python -m pytest","py -m pytest","pytest","dir","ls","type ","cat ","git status","git diff"]
    c = command.strip().lower()
    if not any(c.startswith(x) for x in allowed):
        return "Command blocked. Allowed examples: python app.py, python -m pytest, python -m pip install -r requirements.txt, dir, ls, git status, git diff"
    print_warning("\nThe agent wants to run:")
    print(command)
    print(f"Working directory: {WORKSPACE}")
    if input("Allow command? [y/N]: ").strip().lower() != "y": return "Command cancelled."
    try:
        r = subprocess.run(command, shell=True, cwd=str(WORKSPACE), capture_output=True, text=True, timeout=120)
        output = (r.stdout or "") + (("\nSTDERR:\n" + r.stderr) if r.stderr else "")
        return (output.strip() or f"Command finished with code {r.returncode}")[:MAX_COMMAND_OUTPUT]
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Command error: {e}"


def read_file_with_line_numbers(path: str, start_line: int = 1, end_line: int = 0) -> str:
    """
    Read a file with 1-based line numbers. Useful before patch_lines.
    If end_line is 0, reads to the end.
    """
    try:
        p = safe_path(path)
        if is_ignored(p):
            return "Access denied. Ignored path."
        if not p.exists():
            return f"File does not exist: {path}"
        if not p.is_file():
            return f"Not a file: {path}"
        if p.stat().st_size > MAX_FILE_SIZE:
            return f"File too large. Limit is {MAX_FILE_SIZE} bytes."

        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        if end_line <= 0 or end_line > len(lines):
            end_line = len(lines)
        if start_line < 1:
            start_line = 1
        if start_line > end_line:
            return f"Invalid line range. File has {len(lines)} lines."

        width = len(str(end_line))
        out = []
        for i in range(start_line, end_line + 1):
            out.append(f"{str(i).rjust(width)} | {lines[i - 1]}")
        return "\n".join(out)
    except Exception as e:
        return f"Read numbered file error: {e}"


def create_project_snapshot(name: str = "") -> str:
    """
    Create a zip snapshot of the workspace, excluding ignored folders.
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip("_-")
        filename = f"workspace_{safe_name + '_' if safe_name else ''}{timestamp}.zip"
        zip_path = SNAPSHOT_DIR / filename

        count = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for file in WORKSPACE.rglob("*"):
                if is_ignored(file) or not file.is_file():
                    continue
                z.write(file, file.relative_to(WORKSPACE))
                count += 1

        return f"Snapshot created: {zip_path} ({count} files)"
    except Exception as e:
        return f"Snapshot error: {e}"


def list_backups(path: str = "") -> str:
    """
    List backup files. Optionally filter by original filename substring.
    """
    try:
        rows = []
        needle = path.lower().strip()
        for file in sorted(BACKUP_DIR.rglob("*.bak"), reverse=True):
            rel = str(file.relative_to(BACKUP_DIR))
            if needle and needle not in rel.lower():
                continue
            rows.append(f"{rel} - {file.stat().st_size} bytes")
        return "\n".join(rows[:200]) or "No backups found."
    except Exception as e:
        return f"List backups error: {e}"


def restore_backup(backup_relative_path: str, target_path: str) -> str:
    """
    Restore a backup from BACKUP_DIR into a target path inside WORKSPACE.
    Requires confirmation and creates a backup of the current target first.
    """
    try:
        backup = (BACKUP_DIR / backup_relative_path).resolve()
        backup.relative_to(BACKUP_DIR)

        if not backup.exists() or not backup.is_file():
            return f"Backup not found: {backup_relative_path}"

        target = safe_path(target_path)
        if is_ignored(target):
            return "Restore denied. Ignored path."

        print(f"\nRestore backup:\n  From: {backup}\n  To:   {target}")
        confirm = input("Restore this backup? [y/N]: ").strip().lower()
        if confirm != "y":
            return "Restore cancelled."

        backup_msg = ""
        if target.exists():
            current_backup = make_backup(target)
            backup_msg = f" Current target backed up to: {current_backup}."

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, target)
        return f"Backup restored to: {target.relative_to(WORKSPACE)}.{backup_msg}"
    except Exception as e:
        return f"Restore backup error: {e}"


def write_json_file(path: str, data: str) -> str:
    """
    Validate and write JSON content to a file inside workspace.
    """
    try:
        parsed = json.loads(data)
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"
        return write_text_file(path, pretty)
    except Exception as e:
        return f"Invalid JSON: {e}"


def validate_agent_path(path: str) -> str:
    """
    Show how an agent path will resolve inside WORKSPACE.
    """
    try:
        normalized = normalize_agent_path(path)
        resolved = safe_path(path)
        return (
            f"Input: {path}\n"
            f"Normalized: {normalized or '.'}\n"
            f"Resolved: {resolved}\n"
            f"Relative to workspace: {resolved.relative_to(WORKSPACE) if resolved != WORKSPACE else '.'}"
        )
    except Exception as e:
        return f"Invalid path: {e}"


def export_repo_zip(name: str = "") -> str:
    """
    Create a GitHub-ready repository ZIP, excluding runtime/private files.
    """
    try:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in (name or f"openrouter-agent-v16-3-{stamp}") if c.isalnum() or c in "-_").strip()
        if not safe_name:
            safe_name = f"openrouter-agent-v16-3-{stamp}"

        out = SNAPSHOT_DIR / f"{safe_name}.zip"
        root = Path(".").resolve()

        exclude_dirs = {
            ".git", "__pycache__", ".venv", "venv", "node_modules",
            "logs", "backups", "snapshots", ".pytest_cache", ".mypy_cache", ".ruff_cache",
        }
        exclude_files = {".env", ".openrouter_models_cache.json"}

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for file in root.rglob("*"):
                if not file.is_file():
                    continue

                rel = file.relative_to(root)
                parts = set(rel.parts)

                if parts.intersection(exclude_dirs):
                    continue

                if rel.name in exclude_files:
                    continue

                # Avoid including generated exports recursively.
                if rel.suffix == ".zip":
                    continue

                z.write(file, rel)

        return f"Repository export created: {out}"
    except Exception as e:
        return f"Export repo error: {e}"


def call_provider_with_retries(url, payload, provider, timeout=90):
    last_error = None

    for attempt in range(1, API_RETRY_ATTEMPTS + 1):
        try:
            return http_post_json(url, payload, provider=provider, timeout=timeout)
        except urllib.error.HTTPError:
            raise
        except Exception as e:
            last_error = e
            if attempt < API_RETRY_ATTEMPTS:
                wait = API_RETRY_BASE_SECONDS * attempt
                time.sleep(wait)

    raise RuntimeError(f"API retry failed after {API_RETRY_ATTEMPTS} attempts: {last_error}")


# NOTE:
# Some multi-agent functions are defined later in this file.
# Lambda wrappers below are intentional: they delay name resolution until runtime
# and avoid import-time NameError issues while keeping the file single-script friendly.
TOOLS_MAP = {
    "calculator": calculator, "file_tree": file_tree, "search_files": search_files,
    "read_file_with_line_numbers": read_file_with_line_numbers, "create_project_snapshot": create_project_snapshot,
    "list_backups": list_backups, "restore_backup": restore_backup, "write_json_file": write_json_file,
    "read_text_file": read_text_file, "write_text_file": write_text_file,
    "append_text_file": append_text_file, "replace_in_file": replace_in_file,
    "patch_lines": patch_lines, "create_requirements": create_requirements,
    "inspect_project": inspect_project, "suggest_test_command": suggest_test_command,
    "run_shell_command": run_shell_command, "remember_note": remember_note, "read_memory": read_memory,
    "create_agent_guidance_files": create_agent_guidance_files,
    "list_agent_guidance_files": list_agent_guidance_files,
    "load_agent_guidance": load_agent_guidance,
    "provider_health_dashboard": lambda: provider_health_dashboard(),
    "usage_report": lambda: usage_report(),
    "export_repo_zip": export_repo_zip,
    "validate_agent_path": validate_agent_path,
    "set_auto_mode": lambda value: set_auto_mode(value),
    "set_reviewer_mode": lambda value: set_reviewer_mode(value),
}

def tool_schema(name, description, properties, required=None):
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required or []}}}

TOOLS_SCHEMA = [
    tool_schema("file_tree", "Show recursive file tree inside workspace.", {"path": {"type": "string"}, "max_depth": {"type": "integer"}}, ["path"]),
    tool_schema("search_files", "Search text inside workspace files.", {"query": {"type": "string"}, "path": {"type": "string"}, "extensions": {"type": "string"}}, ["query"]),
    tool_schema("read_text_file", "Read a text file inside workspace.", {"path": {"type": "string"}}, ["path"]),
    tool_schema("write_text_file", "Write a text file inside workspace.", {"path": {"type": "string"}, "content": {"type": "string"}}, ["path","content"]),
    tool_schema("append_text_file", "Append text to a file inside workspace.", {"path": {"type": "string"}, "content": {"type": "string"}}, ["path","content"]),
    tool_schema("replace_in_file", "Replace exact text in a file with diff preview.", {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, ["path","old_text","new_text"]),
    tool_schema("patch_lines", "Replace a 1-based inclusive line range in a file.", {"path": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}, "new_text": {"type": "string"}}, ["path","start_line","end_line","new_text"]),
    tool_schema("create_requirements", "Create requirements.txt from comma-separated packages.", {"packages": {"type": "string"}}, ["packages"]),
    tool_schema("read_file_with_line_numbers", "Read a file with line numbers for safer patching.", {"path": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}}, ["path"]),
    tool_schema("create_project_snapshot", "Create a zip snapshot of the workspace.", {"name": {"type": "string"}}, []),
    tool_schema("list_backups", "List available backup files.", {"path": {"type": "string"}}, []),
    tool_schema("restore_backup", "Restore a backup file into a workspace target path.", {"backup_relative_path": {"type": "string"}, "target_path": {"type": "string"}}, ["backup_relative_path", "target_path"]),
    tool_schema("write_json_file", "Validate and write formatted JSON to a workspace file.", {"path": {"type": "string"}, "data": {"type": "string"}}, ["path", "data"]),
    tool_schema("inspect_project", "Inspect project type and important files.", {}, []),
    tool_schema("suggest_test_command", "Suggest safe test command.", {"project_type": {"type": "string"}}, []),
    tool_schema("run_shell_command", "Run safe whitelisted shell command after confirmation.", {"command": {"type": "string"}}, ["command"]),
    tool_schema("remember_note", "Save useful project memory.", {"note": {"type": "string"}, "project_type": {"type": "string"}}, ["note"]),
    tool_schema("read_memory", "Read saved project memory.", {}, []),
    tool_schema("create_agent_guidance_files", "Create AGENTS.md and SKILL/**/SKILLS.md guidance files.", {"overwrite": {"type": "boolean"}}, []),
    tool_schema("list_agent_guidance_files", "List AGENTS.md and SKILL/**/SKILLS.md guidance files.", {}, []),
    tool_schema("load_agent_guidance", "Load active AGENTS.md and SKILL/**/SKILLS.md guidance text.", {}, []),
    tool_schema("provider_health_dashboard", "Show provider/model health dashboard.", {}, []),
    tool_schema("usage_report", "Show token usage statistics returned by providers.", {}, []),
    tool_schema("export_repo_zip", "Create a GitHub-ready repository ZIP export.", {"name": {"type": "string"}}, []),
    tool_schema("validate_agent_path", "Validate and normalize a path relative to workspace.", {"path": {"type": "string"}}, ["path"]),
    tool_schema("set_auto_mode", "Enable or disable autonomous follow-up mode.", {"value": {"type": "string"}}, ["value"]),
    tool_schema("set_reviewer_mode", "Enable or disable reviewer agent.", {"value": {"type": "string"}}, ["value"]),
]


def route_matches_provider_mode(route):
    provider, _model = parse_model_route(route)
    if PROVIDER_MODE == "auto":
        return True
    return provider == PROVIDER_MODE


def get_active_routes():
    routes = MODELS or DEFAULT_MODELS.copy()
    filtered = [r for r in routes if route_matches_provider_mode(r)]
    return filtered or routes


def update_usage_stats(route, provider, data):
    usage = data.get("usage") or {}
    if not usage:
        return

    prompt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    completion = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    total = int(usage.get("total_tokens") or (prompt + completion))

    USAGE_STATS["calls"] += 1
    USAGE_STATS["prompt_tokens"] += prompt
    USAGE_STATS["completion_tokens"] += completion
    USAGE_STATS["total_tokens"] += total

    by_provider = USAGE_STATS["by_provider"].setdefault(
        provider, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    )
    by_provider["calls"] += 1
    by_provider["prompt_tokens"] += prompt
    by_provider["completion_tokens"] += completion
    by_provider["total_tokens"] += total

    by_route = USAGE_STATS["by_route"].setdefault(
        route, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    )
    by_route["calls"] += 1
    by_route["prompt_tokens"] += prompt
    by_route["completion_tokens"] += completion
    by_route["total_tokens"] += total


def provider_health_dashboard():
    lines = []
    lines.append("Provider Health Dashboard")
    lines.append("=========================")
    lines.append(f"Provider mode: {PROVIDER_MODE}")
    lines.append(f"Active profile: {ACTIVE_PROFILE}")
    lines.append(f"Max steps per task: {MAX_STEPS_PER_TASK}")
    lines.append(f"Max tool iterations per step: {MAX_TOOL_ITERATIONS_PER_STEP}")
    lines.append(f"Temperature: {current_temperature()}")
    lines.append(f"Auto mode: {AUTO_MODE}")
    lines.append(f"Reviewer enabled: {REVIEW_ENABLED}")
    lines.append(f"Auto max rounds: {AUTO_MAX_ROUNDS}")
    lines.append(f"Selected routes: {len(MODELS)}")
    lines.append("")

    stats = MODEL_STATS or {}
    providers = stats.get("providers", {})

    for provider in ["openrouter", "huggingface"]:
        p = providers.get(provider, {})
        lines.append(f"[{provider}]")
        lines.append(f"  enabled: {p.get('enabled')}")
        lines.append(f"  candidates: {len(p.get('candidate_models', []))}")
        lines.append(f"  working chat: {len(p.get('working_chat_models', []))}")
        lines.append(f"  working tools: {len(p.get('working_tool_models', []))}")
        if p.get("working_tool_models"):
            lines.append("  tool models:")
            for m in p.get("working_tool_models", [])[:10]:
                lines.append(f"    - {m}")
        elif p.get("working_chat_models"):
            lines.append("  chat models:")
            for m in p.get("working_chat_models", [])[:10]:
                lines.append(f"    - {m}")
        lines.append("")

    lines.append("Selected routes:")
    for r in MODELS:
        marker = "*" if route_matches_provider_mode(r) else "-"
        lines.append(f"  {marker} {r}")

    return "\n".join(lines)


def usage_report():
    return json.dumps(USAGE_STATS, indent=2, ensure_ascii=False)


def call_openrouter(messages, tools=True, force_no_tools=False):
    """
    Multi-provider chat call.

    Keeps the old function name for compatibility, but routes each model through:
      - OpenRouter:   openrouter::model-id
      - Hugging Face: huggingface::model-id
    """
    last_error = None

    for route in get_active_routes():
        provider, model = parse_model_route(route)
        attempts = [tools, False] if tools and not force_no_tools else [False]

        for attempt_tools in attempts:
            payload = {"model": model, "messages": messages, "temperature": current_temperature()}

            if attempt_tools:
                payload["tools"] = TOOLS_SCHEMA
                payload["tool_choice"] = "auto"

            try:
                data = call_provider_with_retries(
                    provider_chat_url(provider),
                    payload,
                    provider=provider,
                    timeout=90,
                )

                if "error" in data:
                    last_error = f"{route}: {data['error']}"
                    continue

                if "choices" not in data or not data["choices"]:
                    last_error = f"{route}: invalid response without choices"
                    continue

                data["_used_model"] = model
                data["_used_provider"] = provider
                data["_used_route"] = route
                data["_tools_enabled"] = attempt_tools
                update_usage_stats(route, provider, data)

                return data

            except urllib.error.HTTPError as e:
                last_error = f"{route}: HTTP {e.code} - {e.read().decode('utf-8', errors='replace')}"
            except Exception as e:
                last_error = f"{route}: {e}"

    raise RuntimeError(f"All provider/model routes failed. Last error: {last_error}")

def extract_json_object(text):
    try: return json.loads(text)
    except Exception: pass
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1 and e > s:
        return json.loads(text[s:e+1])
    raise ValueError("Could not extract valid JSON.")

def create_plan(user_input):
    memory = load_memory()
    messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user", "content": f"Project memory:\n{json.dumps(memory, ensure_ascii=False)}\n\nUser request:\n{user_input}"},
    ]
    try:
        data = call_openrouter(messages, tools=False, force_no_tools=True)
        content = data["choices"][0]["message"].get("content", "{}")
        return extract_json_object(content)
    except Exception as e:
        print(f"Planner failed, using fallback plan. Reason: {e}")
        return {"goal": user_input[:120], "project_type": memory.get("project_type", "unknown"),
                "steps": [{"id":1,"title":"Inspect project","action":"inspect"},
                          {"id":2,"title":"Apply requested changes","action":"edit"},
                          {"id":3,"title":"Run or suggest safe test","action":"test"}],
                "risk_level":"medium"}

def summarize_if_needed(messages):
    if len(messages) <= MAX_MESSAGES_BEFORE_SUMMARY: return messages
    memory = load_memory()
    old = messages[1:-10]
    prompt = [
        {"role": "system", "content": "Summarize this coding-agent conversation in concise bullets. Mention files changed, decisions, errors, and next steps."},
        {"role": "user", "content": json.dumps(old, ensure_ascii=False)[:40_000]},
    ]
    try:
        data = call_openrouter(prompt, tools=False, force_no_tools=True)
        summary = data["choices"][0]["message"].get("content", "")
        memory["summary"] = summary; save_memory(memory)
        return [messages[0], {"role": "system", "content": f"Previous conversation summary:\n{summary}"}] + messages[-10:]
    except Exception:
        return messages[-15:]

def print_plan(plan):
    if RICH_AVAILABLE:
        table = Table(title="Execution Plan", box=ROUNDED, border_style="cyan")
        table.add_column("Item", style="bold")
        table.add_column("Value")
        table.add_row("Goal", str(plan.get("goal")))
        table.add_row("Project type", str(plan.get("project_type")))
        table.add_row("Risk", str(plan.get("risk_level")))

        steps = Table(title="Steps", box=ROUNDED, border_style="yellow")
        steps.add_column("#", justify="right")
        steps.add_column("Title")
        steps.add_column("Action")
        for step in plan.get("steps", []):
            steps.add_row(str(step.get("id")), str(step.get("title")), str(step.get("action")))

        console.print(table)
        console.print(steps)
        return

    print_info("\nPlan:")
    print_info(f"Goal: {plan.get('goal')}")
    print_info(f"Project type: {plan.get('project_type')}")
    print_info(f"Risk: {plan.get('risk_level')}")
    for step in plan.get("steps", []):
        print_step(f"{step.get('id')}. {step.get('title')} [{step.get('action')}]")
    print()


def reviewer_agent(user_input, plan, execution_result):
    """
    Reviewer agent: checks the output of the executor and decides whether another iteration is needed.
    """
    review_messages = [
        {"role": "system", "content": REVIEWER_PROMPT},
        {
            "role": "user",
            "content": (
                f"Original user request:\n{user_input}\n\n"
                f"Plan:\n{json.dumps(plan, indent=2, ensure_ascii=False)}\n\n"
                f"Execution result:\n{execution_result}\n\n"
                f"Project memory:\n{read_memory()}"
            ),
        },
    ]

    try:
        data = call_openrouter(review_messages, tools=False, force_no_tools=True)
        content = data["choices"][0]["message"].get("content", "{}")
        return extract_json_object(content)
    except Exception as e:
        return {
            "status": "pass",
            "summary": f"Reviewer unavailable, assuming pass. Reason: {e}",
            "issues": [],
            "recommended_next_prompt": "",
        }


def fixer_agent(user_input, review):
    """
    Fixer agent: converts review issues into a focused next execution prompt.
    """
    fixer_messages = [
        {"role": "system", "content": FIXER_PROMPT},
        {
            "role": "user",
            "content": (
                f"Original user request:\n{user_input}\n\n"
                f"Reviewer report:\n{json.dumps(review, indent=2, ensure_ascii=False)}"
            ),
        },
    ]

    try:
        data = call_openrouter(fixer_messages, tools=False, force_no_tools=True)
        content = data["choices"][0]["message"].get("content", "{}")
        return extract_json_object(content)
    except Exception:
        return {
            "fix_goal": "Apply reviewer fixes",
            "user_prompt": review.get("recommended_next_prompt") or "Apply the reviewer recommendations safely.",
        }


def print_review(review):
    if RICH_AVAILABLE:
        table = Table(title="Reviewer Report", box=ROUNDED, border_style="red" if review.get("status") == "needs_fix" else "green")
        table.add_column("Field", style="bold")
        table.add_column("Value")
        table.add_row("Status", str(review.get("status")))
        table.add_row("Summary", str(review.get("summary")))
        table.add_row("Issues", "\n".join(review.get("issues", [])) or "None")
        console.print(table)
    else:
        print_info("\nReviewer Report:")
        print_info(f"Status: {review.get('status')}")
        print_info(f"Summary: {review.get('summary')}")
        issues = review.get("issues", [])
        if issues:
            for i, issue in enumerate(issues, 1):
                print_warning(f"{i}. {issue}")
        else:
            print_success("No issues found.")


def run_review_loop(user_input, plan, messages, execution_result, max_rounds=None):
    """
    Auto mode loop:
    Executor result -> Reviewer -> Fixer -> Executor again if needed.
    """
    final_result = execution_result
    rounds = AUTO_MAX_ROUNDS if max_rounds is None else max_rounds

    if not REVIEW_ENABLED:
        return final_result

    for round_no in range(1, rounds + 1):
        review = reviewer_agent(user_input, plan, final_result)
        print_review(review)

        if review.get("status") != "needs_fix":
            remember_note(f"Reviewer passed task: {review.get('summary', '')}")
            return final_result

        if not AUTO_MODE:
            print_warning("Reviewer requested fixes. Auto mode is OFF, so no follow-up execution was started.")
            remember_note(f"Reviewer requested fixes but auto mode was off: {review.get('summary', '')}")
            return final_result

        fix = fixer_agent(user_input, review)
        next_prompt = fix.get("user_prompt") or review.get("recommended_next_prompt")

        if not next_prompt:
            print_warning("Reviewer requested fixes, but no next prompt was produced.")
            return final_result

        print_step(f"\nAuto round {round_no}: {fix.get('fix_goal', 'Apply fixes')}")
        next_plan = create_plan(next_prompt)
        print_plan(next_plan)
        final_result = execute_plan(next_prompt, next_plan, messages)

    return final_result


def set_auto_mode(value):
    global AUTO_MODE
    value = value.strip().lower()

    if value in {"on", "true", "1", "yes"}:
        AUTO_MODE = True
        return "Auto mode enabled."

    if value in {"off", "false", "0", "no"}:
        AUTO_MODE = True
        return "Auto mode disabled."

    return "Invalid value. Use /auto on or /auto off."


def set_reviewer_mode(value):
    global REVIEW_ENABLED
    value = value.strip().lower()

    if value in {"on", "true", "1", "yes"}:
        REVIEW_ENABLED = True
        return "Reviewer enabled."

    if value in {"off", "false", "0", "no"}:
        REVIEW_ENABLED = False
        return "Reviewer disabled."

    return "Invalid value. Use /review on or /review off."


def set_auto_rounds(value):
    global AUTO_MAX_ROUNDS
    try:
        n = int(value)
    except Exception:
        return "Invalid number. Example: /autorounds 3"

    if n < 1:
        return "Minimum auto rounds is 1."
    if n > 10:
        return "Maximum auto rounds is 10."

    AUTO_MAX_ROUNDS = n
    return f"Auto max rounds set to: {AUTO_MAX_ROUNDS}"


def execute_step(messages, user_input, plan, step):
    messages.append({"role": "user", "content": (
        "Execute only this plan step.\n\n"
        f"Original user request:\n{user_input}\n\n"
        f"Full plan:\n{json.dumps(plan, indent=2, ensure_ascii=False)}\n\n"
        f"Current step:\n{json.dumps(step, indent=2, ensure_ascii=False)}\n\n"
        f"Project memory:\n{read_memory()}\n\nUse tools if useful. Be concise."
    )})
    for _ in range(MAX_TOOL_ITERATIONS_PER_STEP):
        data = call_openrouter(messages, tools=True)
        model = data.get("_used_route", data.get("_used_model", "unknown"))
        tools_enabled = data.get("_tools_enabled", False)
        msg = data["choices"][0].get("message", {})
        messages.append(msg)
        if not tools_enabled:
            return msg.get("content", "Model responded without tool support."), model
        calls = msg.get("tool_calls")
        if not calls:
            return msg.get("content", ""), model
        for call in calls:
            name = call["function"]["name"]
            raw_args = call["function"].get("arguments", "{}")
            try: args = json.loads(raw_args)
            except Exception: args = {}
            tool = TOOLS_MAP.get(name)
            try: result = tool(**args) if tool else f"Unknown tool: {name}"
            except Exception as e: result = f"Tool error: {e}"
            messages.append({"role": "tool", "tool_call_id": call["id"], "name": name, "content": str(result)})
    return f"Step paused after {MAX_TOOL_ITERATIONS_PER_STEP} tool iterations. Increase with /tooliters 30 or use /profile debug if this happens often.", "unknown"

def execute_plan(user_input, plan, messages):
    outputs = []
    for step in plan.get("steps", []):
        rich_panel(f"⚙ Executing step {step.get('id')}: {step.get('title')}", title="Step", style="yellow")
        answer, model = execute_step(messages, user_input, plan, step)
        outputs.append(f"Step {step.get('id')} [{model}]: {answer}")
        print_agent(answer)
    return "\n\n".join(outputs)

def save_session(messages):
    f = LOG_DIR / datetime.now().strftime("session_%Y%m%d_%H%M%S.json")
    f.write_text(json.dumps(messages, indent=2, ensure_ascii=False), encoding="utf-8")
    return f

def print_help():
    print("""
Commands:
  /help                  Show classic help
  /richhelp              Show Rich command dashboard
  /dashboard             Show Rich runtime dashboard
  /auto on|off           Enable/disable autonomous fix loop
  /review on|off         Enable/disable reviewer agent
  /autorounds N          Set max autonomous fix rounds
  /colors                Show terminal color test
  /rich                  Show whether Rich UI is available
  /banner                Show init banner
  /models                Show selected working provider::model routes
  /modelstats            Show discovery stats
  /health                Show provider/model health dashboard
  /usage                 Show token usage stats
  /profiles              List agent profiles
  /tooliters N           Set max tool iterations per step, e.g. /tooliters 30
  /profile NAME          Activate profile: fast, coding, debug, safe, openrouter, huggingface
  /provider MODE         Set provider: auto, openrouter, huggingface
  /hfmodels              Show configured Hugging Face models
  /addhfmodel MODEL      Add Hugging Face model to config
  /removehfmodel MODEL   Remove Hugging Face model from config
  /model ROUTE           Use one route, e.g. openrouter::openrouter/free or huggingface::MODEL
  /resetmodels           Restore discovered/default models
  /discover              Force provider model discovery
  /cacheclear            Clear model discovery cache
  /initguides            Create AGENTS.md and SKILL/**/SKILLS.md files
  /guides                List AGENTS.md and SKILL files
  /guidance              Show active loaded guidance
  /reloadguidance        Reload guidance into active system prompt
  /snapshot NAME         Create a workspace zip snapshot
  /exportrepo [NAME]     Create a GitHub-ready repository ZIP
  /backups [filter]      List backups
  /readlines FILE        Show file with line numbers
  /path PATH             Validate and normalize a workspace-relative path
  /workspace             Show workspace path
  /memory                Show memory
  /inspect               Inspect project
  /testcmd               Suggest test command
  /save                  Save session
  /clear                 Clear conversation memory
  /exit                  Save and exit
""")


def handle_invalid_slash_command(user_input: str) -> bool:
    """
    Return True if the input was an invalid slash command and was handled.
    Example: /pepe
    """
    if not user_input.startswith("/"):
        return False

    valid_prefixes = [
        "/help", "/richhelp", "/dashboard", "/auto ", "/review ", "/autorounds ",
        "/colors", "/rich", "/banner", "/models", "/modelstats", "/health",
        "/usage", "/profiles", "/tooliters ", "/profile ", "/provider ",
        "/hfmodels", "/addhfmodel ", "/removehfmodel ", "/model ", "/resetmodels",
        "/discover", "/cacheclear", "/initguides", "/guides", "/guidance",
        "/reloadguidance", "/exportrepo", "/snapshot", "/backups", "/readlines ",
        "/path ", "/workspace", "/memory", "/inspect", "/testcmd", "/save",
        "/clear", "/exit",
    ]

    for cmd in valid_prefixes:
        if cmd.endswith(" "):
            if user_input.startswith(cmd):
                return False
        else:
            if user_input == cmd:
                return False

    print_error(f"Invalid command: {user_input}")
    print_info("Type /help or /richhelp to see available commands.")
    return True


def main():
    global MODELS
    ensure_env_example()
    ensure_profiles_file()
    load_provider_mode()
    apply_profile(load_profiles().get("active", ACTIVE_PROFILE))

    startup_animation()
    print_dashboard()

    if AUTO_MODE:
        print_info("Auto mode is ENABLED by default. Use /auto off to disable autonomous reviewer fixes.")
    print(f"Workspace:   {WORKSPACE}")
    print(f"Memory:      {MEMORY_FILE}")
    print(f"Logs:        {LOG_DIR}")
    print(f"Backups:     {BACKUP_DIR}")
    print(f"Model cache: {MODEL_CACHE_FILE}")
    print(f"Skill dir:   {SKILL_DIR}")
    print(f"OpenRouter:  {'configured' if OPENROUTER_API_KEY else 'missing OPENROUTER_API_KEY'}")
    print(f"HuggingFace: {'configured' if HF_TOKEN else 'missing HF_TOKEN'}")
    print(f"Provider mode: {PROVIDER_MODE}")
    print(f"Provider config: {PROVIDER_CONFIG_FILE}")
    print(f"Profile config:  {PROFILE_CONFIG_FILE}")
    print(f"Active profile:  {ACTIVE_PROFILE}\n")

    print_info("Ensuring AGENTS.md and SKILL/**/SKILLS.md exist...")
    print(create_agent_guidance_files(overwrite=False))
    print_info("Active guidance files:")
    print(list_agent_guidance_files())
    print()

    if OPENROUTER_API_KEY or HF_TOKEN:
        MODELS = discover_models(force=False)
    else:
        print_warning("No provider credentials found. Set OPENROUTER_API_KEY and/or HF_TOKEN in .env.")
        MODELS = DEFAULT_MODELS.copy()

    print_info("\nSelected models:")
    for m in MODELS: print(f"- {m}")
    print_info("\nType /help for commands.\n")

    messages = [{"role": "system", "content": build_system_prompt()}]

    while True:
        user_input = input(c_user("You: ")).strip()
        if not user_input: continue

        if handle_invalid_slash_command(user_input):
            continue

        if user_input == "/exit":
            print_success(f"Session saved: {save_session(messages)}"); break
        if user_input == "/help": print_help(); continue
        if user_input == "/richhelp": print_help_dashboard(); continue
        if user_input == "/dashboard": print_status_dashboard(); continue
        if user_input == "/rich": print_success("Rich UI enabled." if RICH_AVAILABLE else "Rich UI not installed. Run: python -m pip install rich"); continue
        if user_input.startswith("/auto "): print_info(set_auto_mode(user_input.split(" ", 1)[1])); continue
        if user_input.startswith("/review "): print_info(set_reviewer_mode(user_input.split(" ", 1)[1])); continue
        if user_input.startswith("/autorounds "): print_info(set_auto_rounds(user_input.split(" ", 1)[1])); continue
        if user_input == "/colors":
            print(c_user("User prompt color"))
            print(c_agent("Agent response color"))
            print(c_step("Step/progress color"))
            print(c_info("Info color"))
            print(c_success("Success color"))
            print(c_warning("Warning color"))
            print(c_error("Error color"))
            continue
        if user_input == "/banner": print_banner(); continue
        if user_input == "/models": print_models_table(); continue
        if user_input == "/modelstats": print(json.dumps(MODEL_STATS, indent=2, ensure_ascii=False)); continue
        if user_input == "/health": print_status_dashboard(); continue
        if user_input == "/usage": print(usage_report()); continue
        if user_input == "/profiles": print(list_profiles()); continue
        if user_input.startswith("/tooliters "):
            print(set_tool_iterations(user_input.split(" ", 1)[1].strip()))
            continue
        if user_input.startswith("/profile "):
            print(apply_profile(user_input.split(" ", 1)[1].strip()))
            print_info(f"Provider mode: {PROVIDER_MODE}; max steps: {MAX_STEPS_PER_TASK}; tool iterations: {MAX_TOOL_ITERATIONS_PER_STEP}; temperature: {current_temperature()}")
            continue
        if user_input.startswith("/provider "):
            print(set_provider_mode(user_input.split(" ", 1)[1].strip()))
            continue
        if user_input == "/hfmodels": print("\n".join(get_huggingface_models())); continue
        if user_input.startswith("/addhfmodel "):
            print(add_huggingface_model(user_input.split(" ", 1)[1].strip()))
            print("Run /discover to test the updated Hugging Face model list.")
            continue
        if user_input.startswith("/removehfmodel "):
            print(remove_huggingface_model(user_input.split(" ", 1)[1].strip()))
            print("Run /discover to refresh selected routes.")
            continue
        if user_input.startswith("/model "):
            MODELS = [user_input.split(" ", 1)[1].strip()]
            print_info(f"Model set to: {MODELS[0]}"); continue
        if user_input == "/resetmodels":
            MODELS = MODEL_STATS.get("selected_models") or DEFAULT_MODELS.copy()
            print_info("Models reset."); continue
        if user_input == "/discover":
            if OPENROUTER_API_KEY or HF_TOKEN:
                MODELS = discover_models(force=True)
                print("Selected models:")
                for m in MODELS: print(f"- {m}")
            else:
                print_warning("No provider credentials found. Set OPENROUTER_API_KEY and/or HF_TOKEN.")
            continue
        if user_input == "/cacheclear": print(clear_model_cache()); continue
        if user_input == "/initguides":
            print(create_agent_guidance_files(overwrite=False))
            messages = refresh_system_message(messages)
            print_success("Guidance loaded into active system prompt.")
            continue
        if user_input == "/guides": print(list_agent_guidance_files()); continue
        if user_input == "/guidance": print(load_agent_guidance() or "No active guidance loaded."); continue
        if user_input == "/reloadguidance":
            messages = refresh_system_message(messages)
            print_success("AGENTS.md and SKILL/**/SKILLS.md reloaded into active system prompt.")
            continue

        if user_input.startswith("/exportrepo"):
            parts = user_input.split(" ", 1)
            name = parts[1].strip() if len(parts) > 1 else ""
            print(export_repo_zip(name))
            continue
        if user_input.startswith("/snapshot"):
            parts = user_input.split(" ", 1)
            name = parts[1].strip() if len(parts) > 1 else ""
            print(create_project_snapshot(name))
            continue
        if user_input.startswith("/backups"):
            parts = user_input.split(" ", 1)
            needle = parts[1].strip() if len(parts) > 1 else ""
            print(list_backups(needle))
            continue
        if user_input.startswith("/readlines "):
            file_name = user_input.split(" ", 1)[1].strip()
            print(read_file_with_line_numbers(file_name))
            continue
        if user_input.startswith("/path "):
            print(validate_agent_path(user_input.split(" ", 1)[1].strip()))
            continue
        if user_input == "/workspace": print(WORKSPACE); continue
        if user_input == "/memory": print(read_memory()); continue
        if user_input == "/inspect": print(inspect_project()); continue
        if user_input == "/testcmd":
            print(suggest_test_command(load_memory().get("project_type", "unknown"))); continue
        if user_input == "/save": print_success(f"Session saved: {save_session(messages)}"); continue
        if user_input == "/clear":
            messages = [{"role": "system", "content": build_system_prompt()}]
            print_info("Conversation memory cleared."); continue

        messages = refresh_system_message(messages)
        messages = summarize_if_needed(messages)
        plan = create_plan(user_input)
        print_plan(plan)

        pt = plan.get("project_type", "unknown")
        if pt != "unknown":
            remember_note(f"Detected project type from planner: {pt}", pt)

        result = execute_plan(user_input, plan, messages)
        result = run_review_loop(user_input, plan, messages, result)
        rich_panel(result, title="✔ Final summary", style="green")
        print()

if __name__ == "__main__":
    main()
