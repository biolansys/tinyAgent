# AGENTS.md

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
