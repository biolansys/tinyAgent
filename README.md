# TinyAgent

TinyAgent is a local coding agent centered on [`openrouter_agent_v16_3.py`](C:\Varios\IA\TinyAgent\OpenRouterV16_3\openrouter_agent_v16_3.py). This version is a multi-provider CLI agent that can work with OpenRouter and Hugging Face chat routes, use guided file-editing tools inside `workspace/`, keep project memory, create backups and snapshots, and apply local guidance from `AGENTS.md` and `SKILL/**/SKILLS.md`.

## Current Capabilities

- Multi-provider model routing with `openrouter`, `huggingface`, or `auto` mode.
- Working-model discovery with local cache in `.openrouter_models_cache.json`.
- Interactive coding loop with planning, tool use, and optional reviewer/fixer follow-up rounds.
- Agent profiles for `fast`, `coding`, `debug`, `safe`, `openrouter`, and `huggingface`.
- Safe file operations restricted to `workspace/` for normal project edits.
- Automatic backups before overwrites and ZIP snapshots for larger checkpoints.
- Local project memory stored in `workspace/.agent_memory.json`.
- Guidance loading from `AGENTS.md` and `SKILL/**/SKILLS.md`.
- Optional Rich dashboard UI and colorized terminal output.

## Repository Layout

- [`openrouter_agent_v16_3.py`](C:\Varios\IA\TinyAgent\OpenRouterV16_3\openrouter_agent_v16_3.py): main interactive agent.
- [`run.bat`](C:\Varios\IA\TinyAgent\OpenRouterV16_3\run.bat): Windows launcher.
- [`run.sh`](C:\Varios\IA\TinyAgent\OpenRouterV16_3\run.sh): Unix-like launcher.
- [`AGENTS.md`](C:\Varios\IA\TinyAgent\OpenRouterV16_3\AGENTS.md): repository rules for coding agents.
- [`SKILL/`](C:\Varios\IA\TinyAgent\OpenRouterV16_3\SKILL): reusable guidance packs loaded into the prompt.
- `workspace/`: editable project workspace.
- `logs/`: saved chat sessions.
- `backups/`: backup files created before overwrites.
- `snapshots/`: workspace and repository ZIP exports.
- `.agent_providers.json`: provider config, including Hugging Face model list and provider mode.
- `.agent_profiles.json`: profile definitions and active profile.
- `.openrouter_models_cache.json`: discovered-model cache.

## Requirements

- Python 3.10 or newer.
- At least one provider credential:
  - `OPENROUTER_API_KEY`
  - `HF_TOKEN` or `HUGGINGFACE_API_KEY`
- Internet access for model discovery and chat completions.

Optional terminal packages:

- `colorama` for colored output fallback on Windows.
- `rich` for dashboards, panels, tables, and syntax views.

## Setup

Create a root `.env` file or export the same variables in your shell:

```env
OPENROUTER_API_KEY=your_openrouter_key
HF_TOKEN=your_huggingface_token
# Optional: HF_MODELS=Qwen/Qwen3-Coder-480B-A35B-Instruct,deepseek-ai/DeepSeek-V3-0324
```

Notes:

- OpenRouter-only usage works with just `OPENROUTER_API_KEY`.
- Hugging Face-only usage works with `HF_TOKEN`.
- If `.env.example` is missing, the agent creates it automatically at startup.

## Run

Windows:

```bat
run.bat
```

Unix-like systems:

```bash
./run.sh
```

Direct Python execution:

```bash
python openrouter_agent_v16_3.py
```

## How This Version Works

1. Ensures `.env.example` and profile config files exist.
2. Loads the active profile and provider mode.
3. Creates or verifies `workspace/`, `logs/`, `backups/`, `snapshots/`, and `SKILL/`.
4. Ensures `AGENTS.md` and `SKILL/**/SKILLS.md` guidance files exist.
5. Loads repository guidance into the system prompt.
6. Discovers usable provider routes or falls back to defaults.
7. Builds a short JSON plan for each user request.
8. Executes the plan with tools when needed.
9. Optionally runs reviewer and fixer rounds when auto-review is enabled.
10. Saves sessions, memory, backups, and snapshots locally.

## Built-In Commands

- `/help`
- `/richhelp`
- `/dashboard`
- `/auto on|off`
- `/review on|off`
- `/autorounds N`
- `/colors`
- `/rich`
- `/banner`
- `/models`
- `/modelstats`
- `/health`
- `/usage`
- `/profiles`
- `/tooliters N`
- `/profile NAME`
- `/provider MODE`
- `/hfmodels`
- `/addhfmodel MODEL`
- `/removehfmodel MODEL`
- `/model ROUTE`
- `/resetmodels`
- `/discover`
- `/cacheclear`
- `/initguides`
- `/guides`
- `/guidance`
- `/reloadguidance`
- `/snapshot NAME`
- `/exportrepo [NAME]`
- `/backups [filter]`
- `/readlines FILE`
- `/path PATH`
- `/workspace`
- `/memory`
- `/inspect`
- `/testcmd`
- `/save`
- `/clear`
- `/exit`

## Profiles And Provider Modes

Default profiles:

- `fast`: fewer steps and fewer tool iterations.
- `coding`: balanced default profile.
- `debug`: more tool iterations for troubleshooting.
- `safe`: conservative execution profile.
- `openrouter`: OpenRouter-only route preference.
- `huggingface`: Hugging Face-only route preference.

Provider modes:

- `auto`: try both providers according to available routes.
- `openrouter`: limit execution to OpenRouter routes.
- `huggingface`: limit execution to Hugging Face routes.

## Safety Model

This implementation is intentionally conservative:

- Normal project edits are scoped to `workspace/`.
- Ignored paths include `.git`, virtual environments, caches, and build output directories.
- Shell commands require explicit confirmation from the user.
- Allowed shell commands are restricted to a small safe set such as Python, pip, pytest, `git status`, and `git diff`.
- Backups are created before overwriting files.
- ZIP snapshots and repository exports are available for safer checkpoints.

## Generated Local Files

- `workspace/.agent_memory.json`: persistent project memory.
- `logs/session_YYYYMMDD_HHMMSS.json`: saved chat sessions.
- `backups/**/*.bak`: file backups created before edits.
- `snapshots/*.zip`: workspace snapshots and export archives.
- `.agent_providers.json`: provider preferences and Hugging Face models.
- `.agent_profiles.json`: active profile and profile definitions.

## Notes

- The model cache TTL is 12 hours in the current script.
- Auto-review is enabled by default in this version.
- The current script contains both the main executor loop and the reviewer/fixer logic in one file.
- The app title in the script is `Multi-Provider Python Coding Agent V16.3`.

## License

This repository now uses the MIT License.
