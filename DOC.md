# Temperature and Tool Iterations

## Temperature

`temperature` controls how random or deterministic model output is.

- Lower values like `0.0` to `0.2` produce more stable, focused, repeatable output.
- Medium values like `0.5` produce a balanced mix of stability and variation.
- Higher values like `0.8` to `1.0` produce more varied, creative, less predictable output.

In this app, low temperature is usually better for:

- code edits
- git actions
- file modifications
- structured tasks

Higher temperature is better for:

- brainstorming
- alternative ideas
- exploratory prompts

The current default in this app is `0.2`.

## Tool Iterations

`tooliters` is the maximum number of tool calls the agent can make in one step before it stops that step.

Each file read, file write, git action, shell command, or similar tool call counts toward the limit.

This limit exists to:

- prevent infinite loops
- stop repeated tool cycles
- keep tasks bounded and predictable

If the limit is reached, the app pauses the step instead of continuing forever.

The current default in this app is `25`.

## Practical Use

- Use lower temperature when you want safe, consistent behavior.
- Use higher temperature when you want more creativity.
- Use lower tool iteration limits to stop loops sooner.
- Use higher tool iteration limits only when a task genuinely needs more tool work.

## Recommended Defaults

- Keep `temperature` at `0.2` for coding, git, and file work.
- Raise `temperature` to `0.5` only for broader exploration.
- Keep `tooliters` at `25` as the default.
- Raise `tooliters` to `40` only when the agent is making real progress but needs more tool calls.
- Treat `tooliters` values of `60` or more as exceptional, not normal.
- First reduce task scope or improve the prompt, then raise `tooliters` only if the run is still legitimate and productive.

## When Tool Iterations Are Reached

If the app says `Step paused after N tool iterations`, do this:

1. Inspect the last task or run with `/task ID` or `/run ID`.
2. Check whether the agent was repeating the same read/write/test cycle.
3. Narrow the task scope if the prompt was too broad.
4. Use `/taskretry ID --safe` if you want to rerun the task carefully.
5. Increase `/tooliters` only if the previous run was making real progress.
6. Split the work into smaller tasks if the step is still too large.

Do not blindly raise the limit if the agent was looping or making no progress.

## Auto Mode

`auto mode` controls whether the app keeps executing tasks automatically instead of stopping after each step for manual review.

- `auto on` lets the runtime continue through the task loop on its own.
- `auto off` makes the app stop sooner so you can intervene.
- It is changed with `/auto on|off`.

Related settings:

- `smartauto` decides whether automatic continuation should happen only when it looks sensible.
- `review` controls whether a reviewer pass runs.
- `autorounds` limits how many automatic fix rounds are allowed.
- `tooliters` limits how many tool calls one step can make.

Rule of thumb:

- Use `auto on` for unattended iterative work.
- Use `auto off` when you want tighter control.
- Use `smartauto on` when you want the app to continue only when it appears safe and useful.

## Subagents

Subagents are specialized helper roles that the app can invoke on demand to handle narrow tasks with controlled scope.

- `plan`, `review`, and `search` are read-only specialist subagents.
- `worker` is the write-capable subagent, but only inside an explicit `--file` or `--scope`.
- They are managed by the app, not run separately by the user.

Use them with `/asksubagent`:

- `/asksubagent review "check this file for regressions"`
- `/asksubagent search "find where command history is saved"`
- `/asksubagent plan "outline the next refactor"`
- `/asksubagent worker --file app.py "add docstrings"`
- `/asksubagent worker --scope src "refactor related files"`

Optional flags:

- `--task ID` to attach a specific task context
- `--no-task` to disable task context
- `--preview` to avoid applying worker changes

Best practice:

- Use `plan` first for large tasks.
- Use `search` to find the right files.
- Use `review` before risky changes.
- Use `worker` only when you have a clear ownership scope.

### Main Loop vs Subagents

| Aspect | Main Agent Loop | `review` Subagent | `worker` Subagent |
|---|---|---|---|
| Purpose | Runs the user’s task end to end | Analyzes and critiques | Proposes and applies scoped edits |
| User entrypoint | Normal free-form prompt, `/fix`, `/tests`, `/edit`, etc. | `/asksubagent review ...` | `/asksubagent worker ...` |
| Can write files | Yes | No | Yes, but only inside declared scope |
| Can run tools | Yes | No tools for subagents in current design | No direct tools; patch-based edits only |
| Scope control | Broadest, based on task and app rules | Read-only scope from context | Strict `--file FILE` or `--scope PATH` |
| Output style | Final task result, step logs, review/fix loops | Text analysis and recommendations | Structured JSON patches + diff preview |
| Confirmation | Depends on tool/gith safety rules | Not needed, read-only | Required before applying changes |
| Safety model | Full app safety stack applies | Safest role | Constrained by ownership validation |
| Context used | Full runtime task context, project state, history, checkpoints | Current project + optional task context | Target file/scope + current file contents + optional task context |
| Typical use | Full workflow orchestration | Second opinion | Controlled code changes |
| Best for | Full workflow orchestration | Check bugs, regressions, design issues | Edit one file or bounded set of files |

Rule of thumb:

- Use the main agent loop for normal work.
- Use `review` when you want analysis only.
- Use `worker` when you already know the ownership boundary and want a controlled edit.

## Tkinter System Specs App

If you want to build a Python/Tkinter app that shows system specs, use subagents in stages.

Suggested file structure:

- `app.py` - application entrypoint and Tkinter main window
- `ui.py` - widgets, layout, refresh controls, and view updates
- `system_info.py` - CPU, memory, disk, OS, hostname, and network helpers
- `constants.py` - labels, refresh intervals, and app metadata
- `tests/test_system_info.py` - unit tests for system data collection
- `tests/test_ui.py` - UI behavior tests where practical

Suggested subagent flow:

1. `plan`
   Ask for the architecture and file split first.
   Example: `/asksubagent plan "Design a Python Tkinter app to show system specs. Include modules, UI layout, data sources, and test strategy."`

2. `search`
   Ask where the code should live if the project already has files.
   Example: `/asksubagent search "Find the best place in this project for a Tkinter app entrypoint, UI module, and system info collection."`

3. `worker`
   Use one worker per file or bounded scope.
   Examples:
   - `/asksubagent worker --file app.py "Create the Tkinter main window and wire up the refresh loop."`
   - `/asksubagent worker --file system_info.py "Collect CPU, memory, disk, OS, and hostname information."`
   - `/asksubagent worker --file ui.py "Build the panels and labels for the dashboard."`

4. `review`
   Ask for final quality review before you keep the changes.
   Example: `/asksubagent review "Review this Tkinter app for portability, update handling, and code quality."`

Rule of thumb:

- Use `plan` for the structure.
- Use `worker` for one file or one bounded folder at a time.
- Use `review` before you finalize.
- Use the main agent loop if you want the app to coordinate the whole build for you.

### Tkinter Checklist

For a Tkinter desktop app, use this order:

1. `/asksubagent plan "Design a Tkinter app that shows CPU, memory, disk, OS, and process data."`
2. `/asksubagent search "Find the best file layout for a Tkinter system specs dashboard in this project."`
3. `/asksubagent review "Review this Tkinter app design for cross-platform issues and maintainability."`
4. `/asksubagent worker --file tkinter_app.py "Create the Tkinter entrypoint."`
5. `/asksubagent worker --file tk_specs/system_info.py "Collect system specs and process data."`
6. `/asksubagent worker --file tk_specs/ui.py "Build the dashboard UI."`
7. `/asksubagent review "Review the finished Tkinter dashboard for bugs, layout issues, and code quality."`

### Direct Instruction vs Subagents

Using the main app directly:

- You give one broad instruction.
- The app decides how to break it down.
- It is faster for small tasks.
- It gives less explicit scope and review.
- It is more likely to mix planning, writing, and reviewing in one pass.

Using subagents:

- You split the work into roles.
- Each subagent has a narrower job.
- You can inspect a plan before code changes.
- You can review before applying edits.
- `worker` edits stay bounded to a file or scope.
- This reduces accidental overreach and makes debugging easier.

Rule of thumb:

- Use direct instruction for trivial one-file edits, quick questions, and small experiments.
- Use subagents for multi-file work, risky refactors, new app architecture, and tasks where you want review before write.

### Tkinter Example: Direct vs Subagents

Direct instruction example:

```text
Build a Python/Tkinter app that shows system specs in a dashboard.
```

Expected result:

- The app decides how to split the work.
- You get one broad response or implementation path.
- Planning, implementation, and review may happen in one flow.

Subagent sequence example:

```text
/asksubagent plan "Design a Tkinter app that shows CPU, memory, disk, OS, and processes."
/asksubagent search "Find the best file layout for a Tkinter system specs dashboard in this project."
/asksubagent review "Review this Tkinter app design for cross-platform issues and maintainability."
/asksubagent worker --file tkinter_app.py "Create the Tkinter entrypoint."
/asksubagent worker --file tk_specs/system_info.py "Collect system specs and process data."
/asksubagent worker --file tk_specs/ui.py "Build the dashboard UI."
/asksubagent review "Review the finished Tkinter dashboard for bugs, layout issues, and code quality."
```

Expected output by step:

- `plan`: architecture, module split, UI layout, and implementation sequence.
- `search`: where the app should live in the project and which files matter.
- `review`: risks, missing pieces, and portability issues before coding.
- first `worker`: create the launcher file with a bounded patch.
- second `worker`: create the system info module with a bounded patch.
- third `worker`: create the UI module with a bounded patch.
- final `review`: check the finished code for bugs, layout issues, and code quality.
