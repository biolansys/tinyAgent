import json
try:
    import readline
except Exception:
    readline = None
from . import config
from .state import AgentState
from .providers.discovery import discover_routes, clear_discovery_cache, discovery_report, last_discovery_report, format_discovery_report
from .providers.ranking import ranking_report, reset_rankings, rank_routes
from .providers.client import MultiProviderClient
from .agents.core import AgentRuntime
from .ui import console as ui
from .tools.files import snapshot, export_repo, validate_path, read_file_with_line_numbers
from .tools.shell import run_shell_command
from .guidance import ensure_guidance_files, load_guidance
from .indexer import build_code_index, search_code_index, index_stats, explain_index_file
from .audit import audit_report, clear_audit, history_report, clear_history, task_detail
from .gittools import git_status, git_files, git_diff, git_diff_cached, git_add, git_unstage, git_branch, git_commit, git_init, git_log, git_show, git_restore, git_commit_dry, git_safe_directory
from .memory import load_memory, clear_memory, remember
from .checkpoints import list_checkpoints, load_checkpoint, delete_checkpoint, clear_checkpoints
from .project_context import (
    get_active_project,
    set_active_project,
    create_project,
    clone_project,
    rename_project,
    delete_project,
    project_info,
    list_projects,
    current_project_root,
    project_cmd_commands_file,
    project_memory_file,
    project_session_file,
    project_index_file,
    project_task_history_file,
    project_tool_audit_file,
)


COMMANDS = {
    "/help [COMMAND]": "Show help or details for one command",
    "/dashboard": "Show status dashboard",
    "/models": "Show selected provider::model routes",
    "/discover": "Smart discover using cache, ranking, and early stop",
    "/discoverfull": "Force full discovery without cache or early stop",
    "/discovercache": "Show smart discovery cache report",
    "/cleardiscover": "Clear smart discovery cache",
    "/resetmodels": "Reset model selection to discovered/default routes",
    "/model ROUTE": "Use one specific route, e.g. openrouter::openrouter/free",
    "/provider MODE": "Set provider mode: auto, openrouter, huggingface, mistral",
    "/auto on|off": "Enable/disable autonomous fix loop",
    "/smartauto on|off": "Enable/disable intelligent auto mode",
    "/review on|off": "Enable/disable reviewer agent",
    "/autorounds N": "Set max autonomous fix rounds",
    "/tooliters N": "Set max tool iterations per step",
    "/profiles": "Show available built-in profiles",
    "/profile NAME": "Activate profile: fast, coding, debug, safe, openrouter, huggingface, mistral",
    "/hfmodels": "Show configured Hugging Face models",
    "/addhfmodel MODEL": "Add Hugging Face model for discovery",
    "/removehfmodel MODEL": "Remove Hugging Face model from config",
    "/mistralmodels": "Show configured Mistral models",
    "/addmistralmodel MODEL": "Add Mistral model for discovery",
    "/removemistralmodel MODEL": "Remove Mistral model from config",
    "/snapshot NAME": "Create active project ZIP snapshot",
    "/exportrepo NAME": "Create active project ZIP export",
    "/cmd NAME [ARGS]": "Run one configured OS command",
    "/cmdlist": "Show configured OS commands available to /cmd",
    "/cmdadd NAME COMMAND": "Add or update one configured /cmd command",
    "/cmddel NAME": "Delete one configured /cmd command",
    "/cmdhistory": "Show the last saved user commands for the active project",
    "/path PATH": "Validate and normalize active-project-relative path",
    "/readlines FILE": "Read file with line numbers",
    "/projects": "List projects under workspace",
    "/project NAME": "Switch active project",
    "/projectnew NAME": "Create and switch to a project",
    "/projectclone SRC DEST": "Clone a project and switch to the clone",
    "/projectinfo [NAME]": "Show project information",
    "/projectrename OLD NEW": "Rename a project",
    "/projectdelete NAME": "Delete a project",
    "/projectpath": "Show active project path",
    "/guidance": "Show AGENTS.md + SKILL guidance",
    "/reloadguidance": "Reload AGENTS.md + SKILL guidance",
    "/index": "Build or refresh active project code index",
    "/indexstats": "Show code index statistics",
    "/searchcode QUERY": "Search code index",
    "/explain FILE": "Explain a file using the agent",
    "/reviewfile FILE": "Review a file using the agent",
    "/refactor FILE": "Ask agent for safe refactor suggestions",
    "/fix TEXT": "Ask agent to fix a traceback/error",
    "/tests": "Ask agent to detect and run/suggest tests",
    "/dryrun on|off": "Preview writes/shell commands without executing them",
    "/gitstatus": "Show git status",
    "/gitfiles": "Show changed files in the active project",
    "/gitdiff": "Show git diff",
    "/gitdiffcached": "Show staged git diff",
    "/gitadd": "Stage active project changes",
    "/gitunstage": "Unstage active project changes",
    "/gitlog [N]": "Show recent git commits",
    "/gitshow [REF]": "Show one git revision summary",
    "/gitrestore": "Restore tracked changes in active project",
    "/gitrestore FILE": "Restore tracked changes in one active-project file",
    "/gitcommitdry": "Preview what /gitcommit would commit",
    "/gitinit": "Initialize a git repository",
    "/gitsafedir": "Show the git safe.directory fix for the active project",
    "/gitsafedir apply": "Apply the global git safe.directory fix for the active project",
    "/gitbranch NAME": "Create and switch to a git branch",
    "/gitcommit MESSAGE": "Commit all changes with a message",
    "/history": "Show recent task history",
    "/historyclear": "Clear task history for active project",
    "/task ID": "Show task details",
    "/taskresume ID": "Resume a checkpointed task by ID",
    "/taskretry ID [--tooliters N] [--provider MODE] [--review on|off] [--safe|--force]": "Retry a task from checkpoint input with optional temporary overrides",
    "/runs": "List checkpointed runs for the active project",
    "/run ID": "Show checkpoint details for one run",
    "/runclear ID": "Delete one run checkpoint",
    "/runclearall": "Delete all run checkpoints for the active project",
    "/audit": "Show recent tool audit log",
    "/auditclear": "Clear tool audit log",
    "/memory": "Show project memory",
    "/memoryclear": "Clear project memory",
    "/memorynote TEXT": "Add a note to project memory",
    "/usage": "Show token usage statistics",
    "/ranking": "Show self-optimizing model ranking report",
    "/resetranking": "Reset model ranking statistics",
    "/verbose LEVEL": "Set verbosity level: 0 quiet, 1 normal, 2 detailed, 3 debug",
    "/clear": "Clear conversation memory",
    "/exit": "Exit app",
}

HELP_SECTIONS = [
    ("General", [
        "/help", "/dashboard", "/usage", "/verbose LEVEL", "/clear", "/exit",
    ]),
    ("Projects", [
        "/projects", "/project NAME", "/projectnew NAME", "/projectclone SRC DEST",
        "/projectinfo [NAME]", "/projectrename OLD NEW", "/projectdelete NAME", "/projectpath",
    ]),
    ("Models", [
        "/models", "/model ROUTE", "/provider MODE", "/profiles", "/profile NAME",
        "/hfmodels", "/addhfmodel MODEL", "/removehfmodel MODEL",
        "/mistralmodels", "/addmistralmodel MODEL", "/removemistralmodel MODEL",
    ]),
    ("Discovery", [
        "/discover", "/discoverfull", "/discovercache", "/cleardiscover", "/resetmodels",
        "/ranking", "/resetranking",
    ]),
    ("Automation", [
        "/auto on|off", "/smartauto on|off", "/review on|off", "/autorounds N",
        "/tooliters N", "/dryrun on|off",
    ]),
    ("Files", [
        "/snapshot NAME", "/exportrepo NAME", "/cmdlist", "/cmdadd NAME COMMAND",
        "/cmddel NAME", "/path PATH", "/readlines FILE",
        "/index", "/indexstats", "/searchcode QUERY",
    ]),
    ("Agent Tasks", [
        "/explain FILE", "/reviewfile FILE", "/refactor FILE", "/fix TEXT", "/tests",
    ]),
    ("Git", [
        "/gitstatus", "/gitfiles", "/gitdiff", "/gitdiffcached", "/gitadd", "/gitunstage",
        "/gitlog [N]", "/gitshow [REF]", "/gitrestore", "/gitrestore FILE",
        "/gitcommitdry", "/gitinit", "/gitsafedir", "/gitsafedir apply", "/gitbranch NAME", "/gitcommit MESSAGE",
    ]),
    ("Memory And History", [
        "/memory", "/memoryclear", "/memorynote TEXT", "/cmdhistory", "/history", "/historyclear",
        "/task ID", "/taskresume ID", "/taskretry ID [--tooliters N] [--provider MODE] [--review on|off] [--safe|--force]",
        "/runs", "/run ID", "/runclear ID", "/runclearall", "/audit", "/auditclear",
    ]),
    ("Guidance", [
        "/guidance", "/reloadguidance",
    ]),
]


PROFILES = {
    "fast": {"tooliters": 12, "auto_rounds": 1, "provider": "auto"},
    "coding": {"tooliters": 25, "auto_rounds": 3, "provider": "auto"},
    "debug": {"tooliters": 40, "auto_rounds": 5, "provider": "auto"},
    "safe": {"tooliters": 10, "auto_rounds": 1, "provider": "auto"},
    "openrouter": {"tooliters": 25, "auto_rounds": 3, "provider": "openrouter"},
    "huggingface": {"tooliters": 25, "auto_rounds": 3, "provider": "huggingface"},
    "mistral": {"tooliters": 25, "auto_rounds": 3, "provider": "mistral"},
}

def print_help():
    section_map = {title: [(cmd, COMMANDS[cmd]) for cmd in commands if cmd in COMMANDS] for title, commands in HELP_SECTIONS}
    assigned = {cmd for _title, commands in HELP_SECTIONS for cmd in commands}
    uncategorized = sorted(
        [(cmd, desc) for cmd, desc in COMMANDS.items() if cmd not in assigned],
        key=lambda item: command_base(item[0]),
    )
    if ui.RICH:
        from rich.table import Table
        ui.console.print("Available Commands")
        for title, items in section_map.items():
            if not items:
                continue
            table = Table(title=title)
            table.add_column("Command", style="bold cyan")
            table.add_column("Description")
            for cmd, desc in items:
                table.add_row(cmd, desc)
            ui.console.print(table)
        if uncategorized:
            table = Table(title="Other")
            table.add_column("Command", style="bold cyan")
            table.add_column("Description")
            for cmd, desc in uncategorized:
                table.add_row(cmd, desc)
            ui.console.print(table)
    else:
        print("\nAvailable commands:\n")
        for title, items in section_map.items():
            if not items:
                continue
            print(title)
            for cmd, desc in items:
                print(f"{cmd:<28} {desc}")
        if uncategorized:
            print("Other")
            for cmd, desc in uncategorized:
                print(f"{cmd:<28} {desc}")
        print()


def help_matches(query):
    q = query.strip().lower().lstrip("/")
    if not q:
        return []

    matches = []
    for cmd, desc in COMMANDS.items():
        base = command_base(cmd).lstrip("/").lower()
        full = cmd.lstrip("/").lower()
        if q == base or q == full or q in base or q in full:
            matches.append((cmd, desc))
    return sorted(matches, key=lambda item: (command_base(item[0]) != f"/{q}", command_base(item[0])))


def help_topic_text(query):
    matches = help_matches(query)
    if not matches:
        return f"No help found for: {query}"
    if len(matches) == 1:
        cmd, desc = matches[0]
        return f"{cmd}\n{desc}"
    lines = [f"Matches for '{query}':"]
    for cmd, desc in matches:
        lines.append(f"{cmd:<28} {desc}")
    return "\n".join(lines)


def configured_cmds_text():
    commands = active_cmd_commands()
    if not commands:
        return "No configured commands."
    return "\n".join(f"{name} -> {command}" for name, command in sorted(commands.items()))


def command_history_text(state):
    if not state.command_history:
        return "No saved command history."
    lines = ["Saved command history (oldest to newest):"]
    for i, command in enumerate(state.command_history, start=1):
        lines.append(f"{i:>2}. {command}")
    return "\n".join(lines)

def runs_text():
    rows = list_checkpoints()
    if not rows:
        return "No checkpoints found."
    lines = ["Checkpointed runs:"]
    for row in rows:
        lines.append(
            f"{row.get('task_id')} | status={row.get('status')} | phase={row.get('phase')} | "
            f"next_step={row.get('next_step_index')} | updated={row.get('updated_at')}"
        )
    return "\n".join(lines)


def parse_taskretry(spec):
    parts = str(spec or "").split()
    if not parts:
        return None, None, "Usage: /taskretry ID [--tooliters N] [--provider MODE] [--review on|off] [--safe|--force]"
    task_id = parts[0].strip()
    if not task_id:
        return None, None, "Usage: /taskretry ID [--tooliters N] [--provider MODE] [--review on|off] [--safe|--force]"

    overrides = {"retry_safe_mode": False}
    i = 1
    while i < len(parts):
        flag = parts[i]
        if flag == "--tooliters":
            if i + 1 >= len(parts):
                return None, None, "Missing value for --tooliters"
            try:
                overrides["max_tool_iterations"] = int(parts[i + 1])
            except Exception:
                return None, None, "Invalid integer for --tooliters"
            i += 2
            continue
        if flag == "--provider":
            if i + 1 >= len(parts):
                return None, None, "Missing value for --provider"
            overrides["provider_mode"] = parts[i + 1].strip()
            i += 2
            continue
        if flag == "--review":
            if i + 1 >= len(parts):
                return None, None, "Missing value for --review"
            overrides["review_enabled"] = set_bool(parts[i + 1].strip())
            i += 2
            continue
        if flag == "--safe":
            overrides["retry_safe_mode"] = True
            i += 1
            continue
        if flag == "--force":
            overrides["retry_safe_mode"] = False
            i += 1
            continue
        return None, None, f"Unknown option: {flag}"

    return task_id, overrides, None


def taskretry(runtime, state, spec):
    task_id, overrides, err = parse_taskretry(spec)
    if err:
        return err
    checkpoint = load_checkpoint(task_id)
    if not checkpoint:
        return f"No checkpoint found for task: {task_id}"
    user_input = checkpoint.get("user_input", "")
    if not str(user_input).strip():
        return f"Checkpoint for task {task_id} has no retryable input."

    old_provider = state.provider_mode
    old_tooliters = state.max_tool_iterations
    old_review = state.review_enabled
    old_retry_safe_mode = getattr(state, "retry_safe_mode", False)
    try:
        if "provider_mode" in overrides:
            state.provider_mode = overrides["provider_mode"]
        if "max_tool_iterations" in overrides:
            state.max_tool_iterations = overrides["max_tool_iterations"]
        if "review_enabled" in overrides:
            state.review_enabled = overrides["review_enabled"]
        state.retry_safe_mode = bool(overrides.get("retry_safe_mode", False))
        return runtime.run_task(user_input)
    finally:
        state.provider_mode = old_provider
        state.max_tool_iterations = old_tooliters
        state.review_enabled = old_review
        state.retry_safe_mode = old_retry_safe_mode


def prompt_history_available():
    return readline is not None


def load_prompt_history(state):
    if not prompt_history_available():
        return False
    if hasattr(readline, "clear_history"):
        readline.clear_history()
    else:
        current = readline.get_current_history_length()
        for index in range(current, 0, -1):
            try:
                readline.remove_history_item(index - 1)
            except Exception:
                pass
    if hasattr(readline, "set_history_length"):
        readline.set_history_length(config.MAX_SAVED_COMMAND_HISTORY)
    for command in state.command_history[-config.MAX_SAVED_COMMAND_HISTORY:]:
        readline.add_history(command)
    return True


def append_prompt_history(command):
    if not prompt_history_available():
        return False
    text = str(command).strip()
    if not text:
        return False
    try:
        current = readline.get_current_history_length()
        last = readline.get_history_item(current) if current else None
        if last != text:
            readline.add_history(text)
        return True
    except Exception:
        return False


def read_user_input(prompt_text):
    return input(prompt_text)


def active_cmd_commands():
    commands = config.load_cmd_commands()
    commands.update(config.load_cmd_commands_file(project_cmd_commands_file()))
    return commands


def run_configured_cmd(spec):
    raw = spec.strip()
    if not raw:
        return "Usage: /cmd NAME [ARGS]"
    parts = raw.split(" ", 1)
    name = parts[0].strip()
    extra = parts[1].strip() if len(parts) > 1 else ""
    commands = active_cmd_commands()
    base = commands.get(name)
    if not base:
        available = ", ".join(sorted(commands)) or "none"
        return f"Unknown configured command: {name}\nAvailable commands: {available}"
    full_command = f"{base} {extra}".strip()
    return run_shell_command(full_command, allowed_binaries=config.load_cmd_binaries(commands))


def add_configured_cmd(spec):
    raw = spec.strip()
    parts = raw.split(" ", 1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return "Usage: /cmdadd NAME COMMAND"
    name = parts[0].strip()
    command = parts[1].strip()
    saved = config.add_cmd_command(name, command, path=project_cmd_commands_file())
    return f"Project command saved: {saved} -> {command}"


def remove_configured_cmd(name):
    normalized_name = name.strip()
    if not normalized_name:
        return "Usage: /cmddel NAME"
    try:
        removed = config.remove_cmd_command(normalized_name, path=project_cmd_commands_file())
    except KeyError:
        inherited = config.load_cmd_commands().get(normalized_name)
        if inherited:
            return (
                f"Command '{normalized_name}' is inherited from the repo-level .cmd_commands.json.\n"
                "Edit the repo config file to remove it globally."
            )
        available = ", ".join(sorted(active_cmd_commands())) or "none"
        return f"Unknown configured command: {normalized_name}\nAvailable commands: {available}"
    return f"Project command removed: {removed}"


def command_base(command_pattern: str) -> str:
    return command_pattern.split()[0]


def is_valid_command(user_input: str) -> bool:
    if not user_input.startswith("/"):
        return True

    for pattern in COMMANDS:
        base = command_base(pattern)
        if user_input == base or user_input.startswith(base + " "):
            return True

    return False


def suggest_command(user_input: str) -> str:
    import difflib
    bases = [command_base(cmd) for cmd in COMMANDS]
    matches = difflib.get_close_matches(user_input.split()[0], bases, n=1, cutoff=0.45)
    return matches[0] if matches else ""


def invalid_command(cmd):
    if not cmd.startswith("/"):
        return False

    if is_valid_command(cmd):
        return False

    ui.error(f"Invalid command: {cmd}")
    suggestion = suggest_command(cmd)
    if suggestion:
        ui.info(f"Did you mean: {suggestion} ?")
    ui.info("Type /help to see available commands.")
    return True


def dashboard(state):
    startup_info(state)
    ui.table("Runtime", [
        ("Selected routes", len(state.routes)),
        ("Usage calls", state.usage.get("calls", 0)),
        ("Prompt tokens", state.usage.get("prompt_tokens", 0)),
        ("Completion tokens", state.usage.get("completion_tokens", 0)),
        ("Total tokens", state.usage.get("total_tokens", 0)),
    ])
    if state.routes:
        ui.info("Selected routes:")
        for r in state.routes:
            print("-", r)


def projects_text(active_project):
    projects = list_projects()
    if not projects:
        return "No projects found."
    lines = []
    for name in projects:
        marker = "*" if name == active_project else " "
        suffix = " (active)" if name == active_project else ""
        lines.append(f"{marker} {name}{suffix}")
    return "\n".join(lines)


def project_info_text(name=""):
    info = project_info(name or None)
    return "\n".join([
        f"Name: {info['name']}",
        f"Path: {info['path']}",
        f"Active: {info['active']}",
        f"Files: {info['files']}",
        f"Directories: {info['dirs']}",
        f"Size bytes: {info['bytes']}",
        f"Git repo: {info['has_git']}",
        f"Project AGENTS.md: {info['has_agents']}",
        f"Session file: {info['has_session']}",
    ])


def confirm_project_action(action):
    return input(ui.cyan(f"Confirm {action}? [y/N]: ")).strip().lower() == "y"


def set_bool(value):
    return value.lower() in {"on", "true", "1", "yes"}


def profile_text():
    lines = ["Available profiles:"]
    for name, p in PROFILES.items():
        lines.append(f"- {name}: provider={p['provider']} tooliters={p['tooliters']} autorounds={p['auto_rounds']}")
    return "\n".join(lines)


def apply_profile(state, name):
    if name not in PROFILES:
        return f"Unknown profile: {name}\n{profile_text()}"
    p = PROFILES[name]
    state.provider_mode = p["provider"]
    state.max_tool_iterations = p["tooliters"]
    state.auto_max_rounds = p["auto_rounds"]
    return f"Profile activated: {name}"


def hf_models_file():
    return config.ROOT / ".hf_models"


def get_hf_models():
    p = hf_models_file()
    if p.exists():
        return [x.strip() for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    return config.load_hf_models()


def save_hf_models(models):
    hf_models_file().write_text("\n".join(dict.fromkeys(models)) + "\n", encoding="utf-8")


def add_hf_model(model):
    models = get_hf_models()
    if model not in models:
        models.append(model)
    save_hf_models(models)
    return f"Added Hugging Face model: {model}"


def remove_hf_model(model):
    models = [m for m in get_hf_models() if m != model]
    save_hf_models(models)
    return f"Removed Hugging Face model: {model}"


def mistral_models_file():
    return config.ROOT / ".mistral_models"


def get_mistral_models():
    p = mistral_models_file()
    if p.exists():
        return [x.strip() for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    return config.load_mistral_models()


def save_mistral_models(models):
    mistral_models_file().write_text("\n".join(dict.fromkeys(models)) + "\n", encoding="utf-8")


def add_mistral_model(model):
    models = get_mistral_models()
    if model not in models:
        models.append(model)
    save_mistral_models(models)
    return f"Added Mistral model: {model}"


def remove_mistral_model(model):
    models = [m for m in get_mistral_models() if m != model]
    save_mistral_models(models)
    return f"Removed Mistral model: {model}"



def startup_info(state):
    """
    V17.2 startup dashboard/info screen.
    Restores the rich initialization details from V16.x while keeping the modular architecture.
    """
    ui.banner(config.APP_TITLE, state.provider_mode, state.auto_mode, state.smart_auto)

    rows = [
        ("Workspace", config.WORKSPACE),
        ("Active project", state.active_project),
        ("Project root", current_project_root()),
        ("Logs", config.LOG_DIR),
        ("Backups", config.BACKUP_DIR),
        ("Snapshots", config.SNAPSHOT_DIR),
        ("Skills", config.SKILL_DIR),
        ("Memory", project_memory_file()),
        ("Session", project_session_file()),
        ("Project git repo", (current_project_root() / ".git").exists()),
        ("Project guidance", (current_project_root() / "AGENTS.md").exists()),
        ("Configured /cmd commands", len(active_cmd_commands())),
        ("Saved command history", len(state.command_history)),
        ("Prompt history", "available" if prompt_history_available() else "unavailable"),
        ("OpenRouter", "configured" if config.OPENROUTER_API_KEY else "missing OPENROUTER_API_KEY"),
        ("Hugging Face", "configured" if config.HF_TOKEN else "missing HF_TOKEN"),
        ("Mistral", "configured" if config.MISTRAL_API_KEY else "missing MISTRAL_API_KEY"),
        ("Provider mode", state.provider_mode),
        ("Auto mode", state.auto_mode),
        ("Smart auto", state.smart_auto),
        ("Reviewer", state.review_enabled),
        ("Auto rounds", state.auto_max_rounds),
        ("Tool iterations", state.max_tool_iterations),
        ("Verbose level", state.verbose),
        ("Dry run", state.dry_run),
        ("Ranking file", config.MODEL_RANKING_FILE),
        ("Discovery cache", config.DISCOVERY_CACHE_FILE),
        ("Code index", project_index_file()),
        ("Task history", project_task_history_file()),
        ("Tool audit", project_tool_audit_file()),
        ("Temperature", state.temperature),
    ]

    ui.table("Startup Status", rows)

    ui.info("Active guidance:")
    print("- AGENTS.md")
    print("- SKILL/SKILLS.md")
    print("- SKILL/python/SKILLS.md")
    print("- SKILL/openrouter/SKILLS.md")
    print("- SKILL/safety/SKILLS.md")

    ui.info("Use /help for commands, /dashboard for runtime status, /models for selected routes.")


def set_routes(state, runtime, routes, message="Selected routes:"):
    state.routes = rank_routes(routes)
    runtime.client = MultiProviderClient(state)
    state.save_project_session()
    ui.success(message)
    print("\n".join(state.routes))
    report = last_discovery_report()
    if report:
        ui.panel(format_discovery_report(report), title="Discovery Summary", style="cyan")


def activate_project(state, runtime, project_name, creator):
    state.active_project = creator(project_name)
    state.command_history = []
    state.load_project_session()
    load_prompt_history(state)
    runtime.client = MultiProviderClient(state)
    runtime.reset_messages()
    state.save_project_session()
    ui.success(f"Active project: {state.active_project}")
    ui.info(f"Project root: {current_project_root()}")


def handle_exact_command(user_input, state, runtime):
    if user_input == "/help":
        print_help()
        return True
    if user_input == "/dashboard":
        dashboard(state)
        return True
    if user_input == "/models":
        print("\n".join(state.routes))
        return True
    if user_input == "/discover":
        ui.info("Smart discovering routes with cache + ranking + early stop...")
        set_routes(state, runtime, discover_routes(use_cache=True, early_stop=True))
        return True
    if user_input == "/discoverfull":
        ui.info("Running full discovery without cache or early stop...")
        set_routes(state, runtime, discover_routes(max_checks=0, use_cache=False, early_stop=False))
        return True
    if user_input == "/discovercache":
        print(discovery_report())
        return True
    if user_input == "/cleardiscover":
        print(clear_discovery_cache())
        return True
    if user_input == "/resetmodels":
        state.routes = rank_routes(discover_routes(use_cache=True, early_stop=True))
        runtime.client = MultiProviderClient(state)
        state.save_project_session()
        ui.info("Model routes reset.")
        return True
    if user_input == "/profiles":
        print(profile_text())
        return True
    if user_input == "/hfmodels":
        print("\n".join(get_hf_models()))
        return True
    if user_input == "/mistralmodels":
        print("\n".join(get_mistral_models()))
        return True
    if user_input == "/cmd":
        print("Usage: /cmd NAME [ARGS]")
        print("Configured commands:")
        print(configured_cmds_text())
        return True
    if user_input == "/cmdlist":
        print("Configured commands:")
        print(configured_cmds_text())
        return True
    if user_input == "/cmdhistory":
        print(command_history_text(state))
        return True
    if user_input == "/projects":
        print(projects_text(state.active_project))
        return True
    if user_input == "/projectpath":
        print(current_project_root())
        return True
    if user_input == "/projectinfo":
        print(project_info_text())
        return True
    if user_input == "/guidance":
        print(load_guidance())
        return True
    if user_input == "/reloadguidance":
        runtime.reset_messages()
        ui.success("Guidance reloaded.")
        return True
    if user_input == "/clear":
        runtime.reset_messages()
        ui.info("Conversation memory cleared.")
        return True
    if user_input == "/index":
        print(build_code_index("."))
        return True
    if user_input == "/indexstats":
        print(index_stats())
        return True
    if user_input == "/gitstatus":
        print(git_status())
        return True
    if user_input == "/gitfiles":
        print(git_files())
        return True
    if user_input == "/gitdiff":
        print(git_diff())
        return True
    if user_input == "/gitdiffcached":
        print(git_diff_cached())
        return True
    if user_input == "/gitadd":
        print(git_add())
        return True
    if user_input == "/gitunstage":
        print(git_unstage())
        return True
    if user_input == "/gitrestore":
        print(git_restore())
        return True
    if user_input == "/gitcommitdry":
        print(git_commit_dry())
        return True
    if user_input == "/gitinit":
        print(git_init())
        return True
    if user_input == "/gitsafedir":
        print(git_safe_directory())
        return True
    if user_input == "/history":
        print(history_report())
        return True
    if user_input == "/historyclear":
        print(clear_history())
        return True
    if user_input == "/audit":
        print(audit_report())
        return True
    if user_input == "/auditclear":
        print(clear_audit())
        return True
    if user_input == "/memory":
        print(json.dumps(load_memory(), indent=2, ensure_ascii=False))
        return True
    if user_input == "/memoryclear":
        print(clear_memory())
        return True
    if user_input == "/runs":
        print(runs_text())
        return True
    if user_input == "/runclearall":
        count = clear_checkpoints()
        print(f"Deleted {count} checkpoint(s).")
        return True
    if user_input == "/usage":
        print(json.dumps(state.usage, indent=2))
        return True
    if user_input == "/ranking":
        print(ranking_report())
        return True
    if user_input == "/resetranking":
        print(reset_rankings())
        return True
    if user_input == "/tests":
        result = runtime.run_task("Detect the project type, find the safest test or run command, and execute/suggest it safely.")
        ui.panel(result, title="Tests", style="green")
        return True
    return False


def handle_prefixed_command(user_input, state, runtime):
    if user_input.startswith("/help "):
        print(help_topic_text(user_input.split(" ", 1)[1].strip()))
        return True
    if user_input.startswith("/model "):
        state.routes = [user_input.split(" ", 1)[1].strip()]
        runtime.client = MultiProviderClient(state)
        state.save_project_session()
        ui.info(f"Model route set to: {state.routes[0]}")
        return True
    if user_input.startswith("/profile "):
        print(apply_profile(state, user_input.split(" ", 1)[1].strip()))
        state.save_project_session()
        return True
    if user_input.startswith("/addhfmodel "):
        print(add_hf_model(user_input.split(" ", 1)[1].strip()))
        ui.info("Run /discover to test updated Hugging Face models.")
        return True
    if user_input.startswith("/removehfmodel "):
        print(remove_hf_model(user_input.split(" ", 1)[1].strip()))
        ui.info("Run /discover to refresh routes.")
        return True
    if user_input.startswith("/addmistralmodel "):
        print(add_mistral_model(user_input.split(" ", 1)[1].strip()))
        ui.info("Run /discover to test updated Mistral models.")
        return True
    if user_input.startswith("/removemistralmodel "):
        print(remove_mistral_model(user_input.split(" ", 1)[1].strip()))
        ui.info("Run /discover to refresh routes.")
        return True
    if user_input.startswith("/provider "):
        state.provider_mode = user_input.split(" ", 1)[1].strip()
        state.save_project_session()
        ui.info(f"Provider mode: {state.provider_mode}")
        return True
    if user_input.startswith("/auto "):
        state.auto_mode = set_bool(user_input.split(" ", 1)[1])
        state.save_project_session()
        ui.info(f"Auto mode: {state.auto_mode}")
        return True
    if user_input.startswith("/smartauto "):
        state.smart_auto = set_bool(user_input.split(" ", 1)[1])
        state.save_project_session()
        ui.info(f"Smart auto: {state.smart_auto}")
        return True
    if user_input.startswith("/review "):
        state.review_enabled = set_bool(user_input.split(" ", 1)[1])
        state.save_project_session()
        ui.info(f"Reviewer: {state.review_enabled}")
        return True
    if user_input.startswith("/autorounds "):
        state.auto_max_rounds = int(user_input.split(" ", 1)[1])
        state.save_project_session()
        ui.info(f"Auto rounds: {state.auto_max_rounds}")
        return True
    if user_input.startswith("/tooliters "):
        state.max_tool_iterations = int(user_input.split(" ", 1)[1])
        state.save_project_session()
        ui.info(f"Tool iterations: {state.max_tool_iterations}")
        return True
    if user_input.startswith("/snapshot"):
        name = user_input.split(" ", 1)[1] if " " in user_input else ""
        print(snapshot(name))
        return True
    if user_input.startswith("/exportrepo"):
        name = user_input.split(" ", 1)[1] if " " in user_input else "openrouter-agent-v17"
        print(export_repo(name))
        return True
    if user_input.startswith("/path "):
        print(validate_path(user_input.split(" ", 1)[1]))
        return True
    if user_input.startswith("/readlines "):
        print(read_file_with_line_numbers(user_input.split(" ", 1)[1]))
        return True
    if user_input.startswith("/cmd "):
        print(run_configured_cmd(user_input.split(" ", 1)[1]))
        return True
    if user_input.startswith("/cmdadd "):
        print(add_configured_cmd(user_input.split(" ", 1)[1]))
        return True
    if user_input.startswith("/cmddel "):
        print(remove_configured_cmd(user_input.split(" ", 1)[1]))
        return True
    if user_input.startswith("/projectnew "):
        try:
            activate_project(state, runtime, user_input.split(" ", 1)[1].strip(), create_project)
        except Exception as e:
            ui.error(str(e))
        return True
    if user_input.startswith("/projectclone "):
        try:
            parts = user_input.split()
            if len(parts) != 3:
                ui.warn("Usage: /projectclone SRC DEST")
            else:
                activate_project(state, runtime, parts[2], lambda _target: clone_project(parts[1], parts[2]))
        except Exception as e:
            ui.error(str(e))
        return True
    if user_input.startswith("/projectinfo "):
        try:
            print(project_info_text(user_input.split(" ", 1)[1].strip()))
        except Exception as e:
            ui.error(str(e))
        return True
    if user_input.startswith("/projectrename "):
        try:
            parts = user_input.split()
            if len(parts) != 3:
                ui.warn("Usage: /projectrename OLD NEW")
            else:
                old_name, new_name = parts[1], parts[2]
                if not confirm_project_action(f"rename project '{old_name}' to '{new_name}'"):
                    ui.warn("Project rename cancelled.")
                else:
                    state.active_project = rename_project(old_name, new_name)
                    state.command_history = []
                    state.load_project_session()
                    load_prompt_history(state)
                    runtime.client = MultiProviderClient(state)
                    runtime.reset_messages()
                    state.save_project_session()
                    ui.success(f"Project renamed. Active project: {state.active_project}")
            return True
        except Exception as e:
            ui.error(str(e))
            return True
    if user_input.startswith("/projectdelete "):
        try:
            name = user_input.split(" ", 1)[1].strip()
            if not confirm_project_action(f"delete project '{name}'"):
                ui.warn("Project delete cancelled.")
            else:
                deleted = delete_project(name)
                state.active_project = get_active_project()
                state.command_history = []
                state.load_project_session()
                load_prompt_history(state)
                runtime.client = MultiProviderClient(state)
                runtime.reset_messages()
                state.save_project_session()
                ui.success(f"Deleted project: {deleted}")
                ui.info(f"Active project: {state.active_project}")
            return True
        except Exception as e:
            ui.error(str(e))
            return True
    if user_input.startswith("/project "):
        try:
            activate_project(state, runtime, user_input.split(" ", 1)[1].strip(), set_active_project)
        except Exception as e:
            ui.error(str(e))
        return True
    if user_input.startswith("/searchcode "):
        print(search_code_index(user_input.split(" ", 1)[1].strip()))
        return True
    if user_input.startswith("/explain "):
        target = user_input.split(" ", 1)[1].strip()
        result = runtime.run_task(f"Explain this file clearly. Read it first, summarize purpose, main functions/classes, dependencies, and risks: {target}")
        ui.panel(result, title="File Explanation", style="cyan")
        return True
    if user_input.startswith("/reviewfile "):
        target = user_input.split(" ", 1)[1].strip()
        result = runtime.run_task(f"Review this file for bugs, maintainability, security, and improvement opportunities. Read it first: {target}")
        ui.panel(result, title="File Review", style="yellow")
        return True
    if user_input.startswith("/refactor "):
        target = user_input.split(" ", 1)[1].strip()
        result = runtime.run_task(f"Propose a safe refactor plan for this file. Do not modify unless explicitly necessary and safe. Read it first: {target}")
        ui.panel(result, title="Refactor Suggestions", style="green")
        return True
    if user_input.startswith("/fix "):
        error_text = user_input.split(" ", 1)[1].strip()
        result = runtime.run_task(f"Analyze and fix this error/traceback safely. Inspect relevant files before changing anything. Error: {error_text}")
        ui.panel(result, title="Fix Result", style="red")
        return True
    if user_input.startswith("/dryrun "):
        state.dry_run = set_bool(user_input.split(" ", 1)[1])
        state.save_project_session()
        ui.info(f"Dry run: {state.dry_run}")
        return True
    if user_input.startswith("/gitbranch "):
        print(git_branch(user_input.split(" ", 1)[1].strip()))
        return True
    if user_input.startswith("/gitlog "):
        print(git_log(user_input.split(" ", 1)[1].strip()))
        return True
    if user_input == "/gitlog":
        print(git_log())
        return True
    if user_input.startswith("/gitshow "):
        print(git_show(user_input.split(" ", 1)[1].strip()))
        return True
    if user_input == "/gitshow":
        print(git_show())
        return True
    if user_input.startswith("/gitcommit "):
        print(git_commit(user_input.split(" ", 1)[1].strip()))
        return True
    if user_input.startswith("/gitrestore "):
        print(git_restore(user_input.split(" ", 1)[1].strip()))
        return True
    if user_input == "/gitsafedir apply":
        print(git_safe_directory(apply=True))
        return True
    if user_input.startswith("/task "):
        print(task_detail(user_input.split(" ", 1)[1].strip()))
        return True
    if user_input.startswith("/taskresume "):
        print(runtime.resume_task(user_input.split(" ", 1)[1].strip()))
        return True
    if user_input.startswith("/taskretry "):
        print(taskretry(runtime, state, user_input.split(" ", 1)[1].strip()))
        return True
    if user_input.startswith("/run "):
        task_id = user_input.split(" ", 1)[1].strip()
        data = load_checkpoint(task_id)
        if not data:
            print(f"No checkpoint found for task: {task_id}")
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        return True
    if user_input.startswith("/runclear "):
        task_id = user_input.split(" ", 1)[1].strip()
        if delete_checkpoint(task_id):
            print(f"Checkpoint deleted: {task_id}")
        else:
            print(f"No checkpoint found for task: {task_id}")
        return True
    if user_input.startswith("/memorynote "):
        print(remember(user_input.split(" ", 1)[1].strip()))
        return True
    if user_input.startswith("/verbose "):
        try:
            level = int(user_input.split(" ", 1)[1])
            if level < 0 or level > 3:
                ui.warn("Use /verbose 0, 1, 2, or 3.")
            else:
                state.verbose = level
                state.save_project_session()
                ui.info(f"Verbose level set to {state.verbose}")
        except Exception:
            ui.warn("Usage: /verbose LEVEL")
        return True
    return False


def handle_command(user_input, state, runtime):
    return handle_exact_command(user_input, state, runtime) or handle_prefixed_command(user_input, state, runtime)


def main():
    ensure_guidance_files()
    state = AgentState()
    state.active_project = get_active_project()
    state.load_project_session()
    load_prompt_history(state)

    startup_info(state)

    ui.info("Smart discovering working provider/model routes...")
    state.routes = discover_routes()
    client = MultiProviderClient(state)
    runtime = AgentRuntime(client, state)

    ui.success("Selected routes:")
    for r in state.routes:
        print("-", r)

    ui.info("Initialization complete. Type /help to start.")

    while True:
        user_input = read_user_input(ui.cyan(f"You ({state.active_project}): ")).strip()
        if not user_input:
            continue

        state.record_command(user_input)
        append_prompt_history(user_input)
        state.save_project_session()

        if user_input == "/exit":
            break
        if handle_command(user_input, state, runtime):
            continue

        if invalid_command(user_input):
            continue

        result = runtime.run_task(user_input)
        ui.panel(result, title="Final Summary", style="green")
