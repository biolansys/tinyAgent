import json
from .. import config
from .prompts import PLANNER_PROMPT, REVIEWER_PROMPT, FIXER_PROMPT
from ..guidance import build_system_prompt
from ..memory import read_memory_text, remember
from ..tools.registry import TOOLS, SCHEMAS
from ..ui import console as ui
from ..audit import new_task_id, log_task_start, log_task_plan, log_task_end, log_tool_call
from ..checkpoints import save_checkpoint, load_checkpoint
from ..tools.files import normalize_agent_path
from ..plugins import get_plugin_manager

DRY_RUN_TOOLS = {"write_text_file", "replace_in_file", "patch_lines", "create_requirements", "run_shell_command"}
MUTATING_TOOLS = {
    "write_text_file",
    "replace_in_file",
    "patch_lines",
    "create_requirements",
    "run_shell_command",
    "remember_note",
    "create_project_snapshot",
    "export_repo",
    "build_code_index",
}

def extract_json(text):
    try:
        return json.loads(text)
    except Exception:
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1 and e > s:
            return json.loads(text[s:e+1])
    raise ValueError("Could not extract JSON")


def stringify_review_item(item):
    if isinstance(item, str):
        return item
    if isinstance(item, (dict, list)):
        return json.dumps(item, ensure_ascii=False)
    return str(item)


def tool_call_signature(call):
    name = str(call.get("function", {}).get("name", ""))
    raw = call.get("function", {}).get("arguments", "{}")
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = raw
    try:
        normalized = json.dumps(parsed, sort_keys=True, ensure_ascii=False)
    except Exception:
        normalized = str(parsed)
    return f"{name}:{normalized}"


class AgentRuntime:
    def __init__(self, client, state):
        self.client = client
        self.state = state
        self.messages = []
        self.current_task_id = None
        self.reset_messages()

    def reset_messages(self):
        self.messages = [{"role": "system", "content": build_system_prompt()}]

    def _confirm_retry_mutation(self, tool_name, args):
        if not getattr(self.state, "retry_safe_mode", False):
            return True
        print(
            "\nSafe retry mode: mutating tool call requested.\n"
            f"Tool: {tool_name}\n"
            f"Args: {json.dumps(args, ensure_ascii=False)[:500]}"
        )
        return input("Allow this mutating tool call? [y/N]: ").strip().lower() == "y"

    def _enforce_edit_scope(self, tool_name, args):
        target = str(getattr(self.state, "edit_target_file", "") or "").strip()
        if not target:
            return None

        # In /edit mode, only direct file mutations on the selected file are allowed.
        path_based_tools = {"write_text_file", "replace_in_file", "patch_lines"}
        if tool_name in path_based_tools:
            requested = normalize_agent_path(args.get("path", ""))
            if requested == target:
                return None
            return (
                f"EDIT SCOPE: blocked {tool_name} on '{requested or '.'}'. "
                f"Only '{target}' is allowed in /edit mode."
            )

        if tool_name in MUTATING_TOOLS:
            return (
                f"EDIT SCOPE: blocked mutating tool {tool_name}. "
                f"Only direct edits to '{target}' are allowed in /edit mode."
            )
        return None

    def create_plan(self, user_input):
        msgs = [
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": f"Memory:\n{read_memory_text()}\n\nRequest:\n{user_input}"},
        ]
        try:
            data = self.client.chat(msgs, tools=None, force_no_tools=True)
            return extract_json(data["choices"][0]["message"].get("content", "{}"))
        except Exception as e:
            ui.warn(f"Planner failed, using fallback plan: {e}")
            return {
                "goal": user_input[:120],
                "project_type": "unknown",
                "steps": [
                    {"id": 1, "title": "Inspect project", "action": "inspect"},
                    {"id": 2, "title": "Apply requested changes", "action": "edit"},
                    {"id": 3, "title": "Run or suggest test", "action": "test"},
                ],
                "risk_level": "medium",
            }

    def execute_plan(self, user_input, plan, start_index=0, outputs=None):
        outputs = list(outputs or [])
        steps = plan.get("steps", [])
        for step_index in range(start_index, len(steps)):
            step = steps[step_index]
            if self.state.verbose >= 1:
                ui.panel(f"Executing step {step.get('id')}: {step.get('title')}", title="Step", style="yellow")
            out = self.execute_step(user_input, plan, step)
            outputs.append(f"Step {step.get('id')}: {out}")
            save_checkpoint(self.current_task_id, {
                "status": "in_progress",
                "phase": "execute_plan",
                "user_input": user_input,
                "plan": plan,
                "step_outputs": outputs,
                "next_step_index": step_index + 1,
            })
            ui.agent(out)
        return "\n\n".join(outputs)

    def execute_step(self, user_input, plan, step):
        messages = [{"role": "system", "content": build_system_prompt()}]
        messages.append({"role": "user", "content": (
            f"Execute only this plan step.\n\nRequest:\n{user_input}\n\n"
            f"Plan:\n{json.dumps(plan, indent=2, ensure_ascii=False)}\n\n"
            f"Current step:\n{json.dumps(step, indent=2, ensure_ascii=False)}\n\nMemory:\n{read_memory_text()}"
        )})
        repeat_cycles = 0
        last_cycle_signature = None

        for _ in range(self.state.max_tool_iterations):
            data = self.client.chat(messages, tools=SCHEMAS)
            if self.state.verbose >= 2:
                ui.info(f"Using route: {data.get('_route')} | tools={data.get('_tools_enabled')}")
            msg = data["choices"][0].get("message", {})
            messages.append(msg)
            if not data.get("_tools_enabled"):
                return msg.get("content", "")
            calls = msg.get("tool_calls")
            if not calls:
                return msg.get("content", "")
            cycle_signature = "|".join(tool_call_signature(call) for call in calls)
            if cycle_signature == last_cycle_signature:
                repeat_cycles += 1
            else:
                repeat_cycles = 1
                last_cycle_signature = cycle_signature
            if repeat_cycles >= config.MAX_REPEAT_TOOL_CYCLES:
                return (
                    f"Step paused after detecting {repeat_cycles} repeated tool-call cycles. "
                    f"Last cycle: {cycle_signature[:200]}"
                )
            for call in calls:
                name = call["function"]["name"]
                raw = call["function"].get("arguments", "{}")
                try:
                    args = json.loads(raw)
                except Exception:
                    args = {}
                tool = TOOLS.get(name)
                if self.state.dry_run and name in DRY_RUN_TOOLS:
                    result = f"DRY RUN: would call {name} with args: {args}"
                    messages.append({"role": "tool", "tool_call_id": call["id"], "name": name, "content": str(result)})
                    if self.state.verbose >= 1:
                        ui.warn(result)
                    continue
                scope_block = self._enforce_edit_scope(name, args)
                if scope_block:
                    messages.append({"role": "tool", "tool_call_id": call["id"], "name": name, "content": scope_block})
                    log_tool_call(self.current_task_id, name, args, scope_block)
                    if self.state.verbose >= 1:
                        ui.warn(scope_block)
                    continue
                if name in MUTATING_TOOLS and not self._confirm_retry_mutation(name, args):
                    result = f"SAFE RETRY: blocked mutating tool call {name}."
                    messages.append({"role": "tool", "tool_call_id": call["id"], "name": name, "content": str(result)})
                    log_tool_call(self.current_task_id, name, args, result)
                    if self.state.verbose >= 1:
                        ui.warn(result)
                    continue

                if self.state.verbose >= 2:
                    ui.step(f"Tool call: {name} {args}")
                try:
                    result = tool(**args) if tool else f"Unknown tool: {name}"
                except Exception as e:
                    result = f"Tool error: {e}"
                messages.append({"role": "tool", "tool_call_id": call["id"], "name": name, "content": str(result)})
                log_tool_call(self.current_task_id, name, args, result)
                if self.state.verbose >= 3:
                    ui.info(f"Tool result: {str(result)[:1000]}")
        return f"Step paused after {self.state.max_tool_iterations} tool iterations. Increase with /tooliters 40."

    def reviewer(self, user_input, plan, result):
        msgs = [
            {"role": "system", "content": REVIEWER_PROMPT},
            {"role": "user", "content": f"Request:\n{user_input}\n\nPlan:\n{json.dumps(plan, indent=2, ensure_ascii=False)}\n\nResult:\n{result}"},
        ]
        try:
            data = self.client.chat(msgs, tools=None, force_no_tools=True)
            return extract_json(data["choices"][0]["message"].get("content", "{}"))
        except Exception as e:
            return {"status": "pass", "summary": f"Reviewer unavailable: {e}", "issues": [], "recommended_next_prompt": ""}

    def fixer(self, user_input, review):
        msgs = [
            {"role": "system", "content": FIXER_PROMPT},
            {"role": "user", "content": f"Request:\n{user_input}\n\nReview:\n{json.dumps(review, indent=2, ensure_ascii=False)}"},
        ]
        try:
            data = self.client.chat(msgs, tools=None, force_no_tools=True)
            return extract_json(data["choices"][0]["message"].get("content", "{}"))
        except Exception:
            return {"fix_goal": "Apply fixes", "user_prompt": review.get("recommended_next_prompt", "")}

    def should_auto(self, plan):
        if not self.state.auto_mode:
            return False
        if not self.state.smart_auto:
            return True
        steps = plan.get("steps", [])
        risk = plan.get("risk_level", "low")
        if len(steps) <= 2 and risk == "low":
            return False
        return len(steps) >= 3 or risk in {"medium", "high"}

    def run_task(self, user_input):
        plugin_manager = get_plugin_manager()
        before = plugin_manager.emit_hook(
            "before_task",
            {
                "user_input": user_input,
                "active_project": getattr(self.state, "active_project", ""),
            },
        )
        for warn in before.get("warnings", []):
            ui.warn(f"Plugin hook warning: {warn}")
        if before.get("blocked"):
            return f"Task blocked by plugin hook: {before.get('reason', 'blocked')}"
        user_input = str(before.get("updates", {}).get("user_input", user_input))

        self.current_task_id = new_task_id()
        self.reset_messages()
        log_task_start(self.current_task_id, user_input)
        save_checkpoint(self.current_task_id, {
            "status": "in_progress",
            "phase": "plan",
            "user_input": user_input,
            "next_step_index": 0,
            "step_outputs": [],
        })
        plan = self.create_plan(user_input)
        log_task_plan(self.current_task_id, plan)
        save_checkpoint(self.current_task_id, {
            "status": "in_progress",
            "phase": "execute_plan",
            "user_input": user_input,
            "plan": plan,
            "next_step_index": 0,
            "step_outputs": [],
        })
        self.print_plan(plan)
        result = self.execute_plan(user_input, plan)

        if self.state.review_enabled:
            for round_no in range(1, self.state.auto_max_rounds + 1):
                review = self.reviewer(user_input, plan, result)
                self.print_review(review)
                if review.get("status") != "needs_fix":
                    remember("Reviewer passed: " + review.get("summary", ""))
                    break
                if not self.should_auto(plan):
                    ui.warn("Reviewer requested fixes, but Smart Auto decided not to continue.")
                    break
                fix = self.fixer(user_input, review)
                next_prompt = fix.get("user_prompt") or review.get("recommended_next_prompt")
                if not next_prompt:
                    break
                ui.step(f"Auto round {round_no}: {fix.get('fix_goal', 'Apply fixes')}")
                plan = self.create_plan(next_prompt)
                result = self.execute_plan(next_prompt, plan)
        log_task_end(self.current_task_id, result)
        save_checkpoint(self.current_task_id, {
            "status": "completed",
            "phase": "done",
            "user_input": user_input,
            "plan": plan,
            "next_step_index": len(plan.get("steps", [])),
            "step_outputs": result.split("\n\n") if result else [],
            "result_preview": str(result)[:4000],
        })
        after = plugin_manager.emit_hook(
            "after_task",
            {
                "user_input": user_input,
                "active_project": getattr(self.state, "active_project", ""),
                "task_id": self.current_task_id,
                "result": str(result),
            },
        )
        for warn in after.get("warnings", []):
            ui.warn(f"Plugin hook warning: {warn}")
        return result

    def resume_task(self, task_id):
        checkpoint = load_checkpoint(task_id)
        if not checkpoint:
            return f"No checkpoint found for task: {task_id}"
        if checkpoint.get("status") == "completed":
            preview = checkpoint.get("result_preview", "")
            return f"Task {task_id} is already completed.\n{preview}"
        plan = checkpoint.get("plan")
        user_input = checkpoint.get("user_input", "")
        if not isinstance(plan, dict):
            return f"Checkpoint for task {task_id} has no resumable plan."

        self.current_task_id = task_id
        self.reset_messages()
        start_index = int(checkpoint.get("next_step_index", 0))
        step_outputs = checkpoint.get("step_outputs", [])
        if not isinstance(step_outputs, list):
            step_outputs = []

        result = self.execute_plan(user_input, plan, start_index=start_index, outputs=step_outputs)
        if self.state.review_enabled:
            review = self.reviewer(user_input, plan, result)
            self.print_review(review)
        log_task_end(self.current_task_id, result)
        save_checkpoint(self.current_task_id, {
            "status": "completed",
            "phase": "done",
            "user_input": user_input,
            "plan": plan,
            "next_step_index": len(plan.get("steps", [])),
            "step_outputs": result.split("\n\n") if result else [],
            "result_preview": str(result)[:4000],
        })
        return result

    def print_plan(self, plan):
        ui.table("Execution Plan", [
            ("Goal", plan.get("goal")),
            ("Project type", plan.get("project_type")),
            ("Risk", plan.get("risk_level")),
            ("Steps", len(plan.get("steps", []))),
        ])

    def print_review(self, review):
        issues = review.get("issues", [])
        if not isinstance(issues, list):
            issues = [issues]
        ui.table("Reviewer Report", [
            ("Status", review.get("status")),
            ("Summary", review.get("summary")),
            ("Issues", "\n".join(stringify_review_item(item) for item in issues if item is not None) or "None"),
        ])
