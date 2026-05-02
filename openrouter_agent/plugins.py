import importlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PluginCommand:
    name: str
    description: str
    handler: object
    plugin_name: str


@dataclass
class PluginHook:
    hook: str
    handler: object
    plugin_name: str
    priority: int
    capabilities: set


class PluginManager:
    def __init__(self):
        self.commands = {}
        self.hooks = {}
        self.errors = []

    def load_manifest(self, path: Path):
        self.commands = {}
        self.hooks = {}
        self.errors = []
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.errors.append(f"Plugin manifest read error: {exc}")
            return

        if not isinstance(data, dict):
            self.errors.append("Plugin manifest must be a JSON object.")
            return
        plugins = data.get("plugins", [])
        if not isinstance(plugins, list):
            self.errors.append("Plugin manifest field 'plugins' must be a list.")
            return

        for item in plugins:
            self._load_plugin_spec(item)

    def _load_plugin_spec(self, item):
        if not isinstance(item, dict):
            self.errors.append("Invalid plugin item (expected object).")
            return
        plugin_name = str(item.get("name", "")).strip() or "unnamed"
        module_name = str(item.get("module", "")).strip()
        command_items = item.get("commands", [])
        hook_items = item.get("hooks", [])
        priority = int(item.get("priority", 100))
        caps_raw = item.get("capabilities", [])
        capabilities = {str(x).strip() for x in caps_raw if str(x).strip()} if isinstance(caps_raw, list) else set()
        if not module_name:
            self.errors.append(f"Plugin '{plugin_name}' missing module.")
            return
        if not isinstance(command_items, list):
            self.errors.append(f"Plugin '{plugin_name}' commands must be a list.")
            return
        if not isinstance(hook_items, list):
            self.errors.append(f"Plugin '{plugin_name}' hooks must be a list.")
            return

        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            self.errors.append(f"Plugin '{plugin_name}' import error: {exc}")
            return

        for command_item in command_items:
            self._load_command_spec(plugin_name, module, command_item)
        for hook_item in hook_items:
            self._load_hook_spec(plugin_name, module, hook_item, priority, capabilities)

    def _load_command_spec(self, plugin_name, module, command_item):
        if not isinstance(command_item, dict):
            self.errors.append(f"Plugin '{plugin_name}' has invalid command item.")
            return
        name = str(command_item.get("name", "")).strip()
        description = str(command_item.get("description", "")).strip() or "Plugin command"
        handler_name = str(command_item.get("handler", "")).strip()
        if not name.startswith("/"):
            self.errors.append(f"Plugin '{plugin_name}' command must start with '/': {name}")
            return
        if not handler_name:
            self.errors.append(f"Plugin '{plugin_name}' command {name} missing handler.")
            return
        handler = getattr(module, handler_name, None)
        if not callable(handler):
            self.errors.append(f"Plugin '{plugin_name}' handler not callable: {handler_name}")
            return
        self.commands[name] = PluginCommand(
            name=name,
            description=description,
            handler=handler,
            plugin_name=plugin_name,
        )

    def get_help_entries(self):
        return {name: command.description for name, command in self.commands.items()}

    def _capability_required_for_hook(self, hook_name):
        if hook_name == "on_project_created":
            return "project_hooks"
        if hook_name in {"before_task", "after_task"}:
            return "task_hooks"
        return None

    def _load_hook_spec(self, plugin_name, module, hook_item, priority, capabilities):
        if not isinstance(hook_item, dict):
            self.errors.append(f"Plugin '{plugin_name}' has invalid hook item.")
            return
        hook_name = str(hook_item.get("name", "")).strip()
        handler_name = str(hook_item.get("handler", "")).strip()
        if not hook_name:
            self.errors.append(f"Plugin '{plugin_name}' hook missing name.")
            return
        if not handler_name:
            self.errors.append(f"Plugin '{plugin_name}' hook '{hook_name}' missing handler.")
            return
        required = self._capability_required_for_hook(hook_name)
        if required and required not in capabilities:
            self.errors.append(
                f"Plugin '{plugin_name}' hook '{hook_name}' requires capability '{required}'."
            )
            return
        handler = getattr(module, handler_name, None)
        if not callable(handler):
            self.errors.append(f"Plugin '{plugin_name}' hook handler not callable: {handler_name}")
            return
        self.hooks.setdefault(hook_name, []).append(
            PluginHook(
                hook=hook_name,
                handler=handler,
                plugin_name=plugin_name,
                priority=priority,
                capabilities=capabilities,
            )
        )
        self.hooks[hook_name] = sorted(
            self.hooks[hook_name],
            key=lambda item: (item.priority, item.plugin_name),
        )

    def run(self, user_input, state, runtime):
        text = str(user_input or "").strip()
        if not text.startswith("/"):
            return False, None
        command_name = text.split(" ", 1)[0]
        command = self.commands.get(command_name)
        if not command:
            return False, None
        args = text[len(command_name):].strip()
        try:
            result = command.handler(args=args, state=state, runtime=runtime)
        except Exception as exc:
            return True, f"Plugin '{command.plugin_name}' command failed: {exc}"
        return True, result

    def emit_hook(self, hook_name, context):
        handlers = self.hooks.get(str(hook_name).strip(), [])
        updates = {}
        warnings = []
        for hook in handlers:
            try:
                result = hook.handler(context=dict(context), plugin=hook.plugin_name)
            except Exception as exc:
                self.errors.append(f"Plugin '{hook.plugin_name}' hook '{hook_name}' failed: {exc}")
                continue
            if not isinstance(result, dict):
                continue
            action = str(result.get("action", "continue")).strip().lower()
            if action == "block":
                return {
                    "blocked": True,
                    "reason": str(result.get("reason", "Blocked by plugin hook.")),
                    "updates": updates,
                    "warnings": warnings,
                }
            if action == "mutate":
                hook_updates = result.get("updates", {})
                if isinstance(hook_updates, dict):
                    updates.update(hook_updates)
            if action == "warn":
                msg = str(result.get("message", "")).strip()
                if msg:
                    warnings.append(msg)
        return {"blocked": False, "reason": "", "updates": updates, "warnings": warnings}


_PLUGIN_MANAGER = PluginManager()


def get_plugin_manager():
    return _PLUGIN_MANAGER

