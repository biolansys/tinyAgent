# TinyAgent

TinyAgent is a lightweight local coding agent built around the OpenRouter chat completions API. It is designed to work inside a controlled `workspace/`, use a small set of safe tools, keep local memory, create backups before edits, and follow repository guidance from `AGENTS.md` and `SKILL/**/SKILLS.md`.

## What It Does

- Discovers and caches working free OpenRouter models.
- Builds plans for user requests before executing them.
- Uses structured tools for file reads, edits, search, backups, snapshots, and safe shell commands.
- Restricts file edits to the local `workspace/` directory.
- Loads repository guidance files into the active system prompt.
- Stores simple project memory between interactions.

## Repository Layout

- `openrouter_agent_v10.py`: main interactive agent.
- `workspace/`: project files the agent is allowed to inspect and edit.
- `SKILL/`: reusable instruction packs loaded into the agent prompt.
- `backups/`: automatic file backups created before overwrites.
- `snapshots/`: zip snapshots of the workspace for larger changes.
- `logs/`: saved conversation sessions.
- `AGENTS.md`: local behavioral and safety rules for agents working in this repo.

## How The Agent Works

1. Starts the local CLI agent.
2. Ensures guidance files exist.
3. Loads `AGENTS.md` and `SKILL/**/SKILLS.md` into the system prompt.
4. Discovers usable OpenRouter models, with a local cache fallback.
5. Creates a short JSON plan for each user request.
6. Executes the plan step by step using tool calls when appropriate.
7. Saves session logs, backups, snapshots, and project memory locally.

## Requirements

- Python 3.10+ recommended.
- An OpenRouter API key.
- Internet access for model discovery and chat completions.

Optional libraries are needed for some example scripts in `workspace/`, including:

- `duckdb`
- `pandas`
- `matplotlib`
- `mysql-connector-python`

## Setup

1. Create an `.env` file in the repository root.
2. Add your OpenRouter key:

```env
OPENROUTER_API_KEY=your_api_key_here
```

You can also export `OPENROUTER_API_KEY` as an environment variable instead of using `.env`.

## Run

On Windows:

```bat
run.bat
```

On Unix-like systems:

```bash
./run.sh
```

Or run the agent directly:

```bash
python openrouter_agent_v10.py
```

## Built-In Commands

The CLI supports direct commands such as:

- `/help`
- `/models`
- `/modelstats`
- `/discover`
- `/cacheclear`
- `/guides`
- `/guidance`
- `/reloadguidance`
- `/snapshot NAME`
- `/backups [filter]`
- `/readlines FILE`
- `/workspace`
- `/memory`
- `/inspect`
- `/testcmd`
- `/save`
- `/clear`
- `/exit`

## Safety Model

The agent is intentionally conservative:

- It works inside `workspace/` for normal file operations.
- It ignores noisy or risky directories such as `.git`, virtual environments, and build outputs.
- It asks for confirmation before shell commands.
- It previews diffs for targeted text replacements and line patches.
- It creates backups before overwriting files.
- It can create full workspace snapshots before larger changes.

## Example Workspace Content

The repository currently includes simple example scripts in `workspace/`:

- data visualization for CSV and Parquet files
- system information HTML generation
- SQLite, DuckDB, and MariaDB connection examples

These are useful as sample targets for the agent, but they are not the core agent implementation.

## Notes

- Model discovery is cached in `.openrouter_models_cache.json`.
- Project memory is stored in `workspace/.agent_memory.json`.
- Session logs are written to `logs/`.
- The current implementation is centered in a single Python file for simplicity.

## Roadmap Ideas

- Split the monolithic agent into smaller modules.
- Add automated tests for tool safety and planning behavior.
- Add a dependency manifest such as `requirements.txt` or `pyproject.toml`.
- Improve packaging and installation.

## License

No license file is currently included in this repository.
