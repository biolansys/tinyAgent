import json
from dataclasses import dataclass, field
from . import config
from .project_context import get_active_project
from .project_context import project_session_file

@dataclass
class AgentState:
    routes: list[str] = field(default_factory=lambda: config.DEFAULT_ROUTES.copy())
    active_project: str = field(default_factory=get_active_project)
    provider_mode: str = config.PROVIDER_MODE
    auto_mode: bool = config.AUTO_MODE
    smart_auto: bool = config.SMART_AUTO_MODE
    review_enabled: bool = config.REVIEW_ENABLED
    auto_max_rounds: int = config.AUTO_MAX_ROUNDS
    max_tool_iterations: int = config.MAX_TOOL_ITERATIONS_PER_STEP
    temperature: float = config.TEMPERATURE
    verbose: int = config.VERBOSE_LEVEL
    dry_run: bool = config.DRY_RUN
    usage: dict = field(default_factory=lambda: {
        "calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "by_route": {},
    })
    command_history: list[str] = field(default_factory=list)

    def route_allowed(self, route: str) -> bool:
        if self.provider_mode == "auto":
            return True
        return route.startswith(self.provider_mode + "::")

    def session_payload(self) -> dict:
        return {
            "routes": list(self.routes),
            "provider_mode": self.provider_mode,
            "auto_mode": self.auto_mode,
            "smart_auto": self.smart_auto,
            "review_enabled": self.review_enabled,
            "auto_max_rounds": self.auto_max_rounds,
            "max_tool_iterations": self.max_tool_iterations,
            "temperature": self.temperature,
            "verbose": self.verbose,
            "dry_run": self.dry_run,
            "command_history": list(self.command_history[-config.MAX_SAVED_COMMAND_HISTORY:]),
        }

    def record_command(self, command: str):
        text = str(command).strip()
        if not text:
            return
        self.command_history.append(text)
        self.command_history = self.command_history[-config.MAX_SAVED_COMMAND_HISTORY:]

    def load_project_session(self):
        path = project_session_file()
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return False
        if isinstance(data.get("routes"), list) and data["routes"]:
            self.routes = [str(x) for x in data["routes"] if str(x).strip()]
        self.provider_mode = str(data.get("provider_mode", self.provider_mode))
        self.auto_mode = bool(data.get("auto_mode", self.auto_mode))
        self.smart_auto = bool(data.get("smart_auto", self.smart_auto))
        self.review_enabled = bool(data.get("review_enabled", self.review_enabled))
        self.auto_max_rounds = int(data.get("auto_max_rounds", self.auto_max_rounds))
        self.max_tool_iterations = int(data.get("max_tool_iterations", self.max_tool_iterations))
        self.temperature = float(data.get("temperature", self.temperature))
        self.verbose = int(data.get("verbose", self.verbose))
        self.dry_run = bool(data.get("dry_run", self.dry_run))
        if isinstance(data.get("command_history"), list):
            self.command_history = [
                str(x).strip()
                for x in data["command_history"]
                if str(x).strip()
            ][-config.MAX_SAVED_COMMAND_HISTORY:]
        return True

    def save_project_session(self):
        project_session_file().write_text(
            json.dumps(self.session_payload(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
