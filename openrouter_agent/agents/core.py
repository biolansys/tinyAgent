import json
from .prompts import PLANNER_PROMPT, REVIEWER_PROMPT, FIXER_PROMPT
from ..guidance import build_system_prompt
from ..memory import read_memory_text, remember
from ..tools.registry import TOOLS, SCHEMAS
from ..ui import console as ui
from ..audit import new_task_id, log_task_start, log_task_plan, log_task_end, log_tool_call

DRY_RUN_TOOLS = {"write_text_file", "replace_in_file", "patch_lines", "create_requirements", "run_shell_command"}

def extract_json(text):
    try:
        return json.loads(text)
    except Exception:
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1 and e > s:
            return json.loads(text[s:e+1])
    raise ValueError("Could not extract JSON")

class AgentRuntime:
    def __init__(self, client, state):
        self.client = client
        self.state = state
        self.messages = []
        self.current_task_id = None
        self.reset_messages()

    def reset_messages(self):
        self.messages = [{"role": "system", "content": build_system_prompt()}]

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

    def execute_plan(self, user_input, plan):
        outputs = []
        for step in plan.get("steps", []):
            if self.state.verbose >= 1:
                ui.panel(f"Executing step {step.get('id')}: {step.get('title')}", title="Step", style="yellow")
            out = self.execute_step(user_input, plan, step)
            outputs.append(f"Step {step.get('id')}: {out}")
            ui.agent(out)
        return "\n\n".join(outputs)

    def execute_step(self, user_input, plan, step):
        messages = [{"role": "system", "content": build_system_prompt()}]
        messages.append({"role": "user", "content": (
            f"Execute only this plan step.\n\nRequest:\n{user_input}\n\n"
            f"Plan:\n{json.dumps(plan, indent=2, ensure_ascii=False)}\n\n"
            f"Current step:\n{json.dumps(step, indent=2, ensure_ascii=False)}\n\nMemory:\n{read_memory_text()}"
        )})

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
        self.current_task_id = new_task_id()
        self.reset_messages()
        log_task_start(self.current_task_id, user_input)
        plan = self.create_plan(user_input)
        log_task_plan(self.current_task_id, plan)
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
        return result

    def print_plan(self, plan):
        ui.table("Execution Plan", [
            ("Goal", plan.get("goal")),
            ("Project type", plan.get("project_type")),
            ("Risk", plan.get("risk_level")),
            ("Steps", len(plan.get("steps", []))),
        ])

    def print_review(self, review):
        ui.table("Reviewer Report", [
            ("Status", review.get("status")),
            ("Summary", review.get("summary")),
            ("Issues", "\n".join(review.get("issues", [])) or "None"),
        ])
