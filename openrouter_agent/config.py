import json
from pathlib import Path
import os

APP_TITLE = "OpenRouter Agent V21 Production"

ROOT = Path(".").resolve()
WORKSPACE = (ROOT / "workspace").resolve()
LOG_DIR = (ROOT / "logs").resolve()
BACKUP_DIR = (ROOT / "backups").resolve()
SNAPSHOT_DIR = (ROOT / "snapshots").resolve()
SKILL_DIR = (ROOT / "SKILL").resolve()
MEMORY_FILE = WORKSPACE / ".agent_memory.json"
CMD_COMMANDS_FILE = ROOT / ".cmd_commands.json"

for d in [WORKSPACE, LOG_DIR, BACKUP_DIR, SNAPSHOT_DIR, SKILL_DIR]:
    d.mkdir(parents=True, exist_ok=True)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODELS_URL = "https://api.mistral.ai/v1/models"

DEFAULT_OPENROUTER_MODELS = ["openrouter/free"]
DEFAULT_HF_MODELS = [
    "Qwen/Qwen3-Coder-480B-A35B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",    
    "openai/gpt-oss-120b",
    "Qwen/Qwen2.5-Coder-32B-Instruct"
]
DEFAULT_MISTRAL_MODELS = [
    "mistral-small-latest",
    "mistral-medium-latest",
    "codestral-latest",
]
DEFAULT_ROUTES = ["openrouter::openrouter/free"]
DEFAULT_CMD_COMMANDS = {
    "dir": "dir",
    "ls": "ls",
    "pwd": "pwd"
}

MAX_FILE_SIZE = 300_000
MAX_COMMAND_OUTPUT = 25_000
MAX_TOOL_ITERATIONS_PER_STEP = 25
AUTO_MODE = True
SMART_AUTO_MODE = True
REVIEW_ENABLED = True
AUTO_MAX_ROUNDS = 3
PROVIDER_MODE = "auto"
TEMPERATURE = 0.2
VERBOSE_LEVEL = 1
MODEL_RANKING_FILE = ROOT / ".model_ranking.json"
DISCOVERY_CACHE_FILE = ROOT / ".model_discovery_cache.json"
DISCOVERY_CACHE_TTL_MINUTES = 720
DISCOVERY_MAX_CHECKS_PER_PROVIDER = 12
DISCOVERY_TARGET_WORKING_ROUTES = 6
DISCOVERY_MIN_WORKING_ROUTES = 3
CODE_INDEX_FILE = ROOT / ".code_index.json"
DRY_RUN = False
TOOL_AUDIT_FILE = LOG_DIR / "tool_audit.jsonl"
TASK_HISTORY_FILE = LOG_DIR / "task_history.jsonl"
MAX_SAVED_COMMAND_HISTORY = 50

IGNORE_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    "dist", "build", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}

def load_env_value(name: str):
    if os.getenv(name):
        return os.getenv(name)
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None

OPENROUTER_API_KEY = load_env_value("OPENROUTER_API_KEY")
HF_TOKEN = load_env_value("HF_TOKEN") or load_env_value("HUGGINGFACE_API_KEY")
MISTRAL_API_KEY = load_env_value("MISTRAL_API_KEY")

def load_hf_models():
    raw = load_env_value("HF_MODELS")
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    return DEFAULT_HF_MODELS.copy()


def load_mistral_models():
    raw = load_env_value("MISTRAL_MODELS")
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    return DEFAULT_MISTRAL_MODELS.copy()


def load_cmd_commands_file(path):
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = None
        if isinstance(data, dict):
            commands = {}
            for key, value in data.items():
                name = str(key).strip()
                command = str(value).strip()
                if name and command:
                    commands[name] = command
            return commands
    return {}


def load_cmd_commands():
    commands = load_cmd_commands_file(CMD_COMMANDS_FILE)
    if commands:
        return commands
    return DEFAULT_CMD_COMMANDS.copy()


def load_cmd_binaries(commands=None):
    binaries = set()
    for command in (commands or load_cmd_commands()).values():
        parts = str(command).strip().split()
        if parts:
            binaries.add(parts[0].lower())
    return binaries


def save_cmd_commands(commands, path=None):
    data = {
        str(name).strip(): str(command).strip()
        for name, command in commands.items()
        if str(name).strip() and str(command).strip()
    }
    target = path or CMD_COMMANDS_FILE
    target.write_text(json.dumps(dict(sorted(data.items())), indent=2) + "\n", encoding="utf-8")


def add_cmd_command(name, command, path=None):
    commands = load_cmd_commands_file(path or CMD_COMMANDS_FILE)
    normalized_name = str(name).strip()
    normalized_command = str(command).strip()
    if not normalized_name or not normalized_command:
        raise ValueError("Command name and command text are required.")
    commands[normalized_name] = normalized_command
    save_cmd_commands(commands, path=path)
    return normalized_name


def remove_cmd_command(name, path=None):
    commands = load_cmd_commands_file(path or CMD_COMMANDS_FILE)
    normalized_name = str(name).strip()
    if normalized_name not in commands:
        raise KeyError(normalized_name)
    del commands[normalized_name]
    save_cmd_commands(commands, path=path)
    return normalized_name
