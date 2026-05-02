# OpenRouter Agent V21 Production

Multi-provider coding agent with active-project isolation under `workspace/`.

## Overview

The app is a local CLI coding agent that can:

- route requests through OpenRouter or Hugging Face
- discover working free or configured models
- operate on one active project at a time inside `workspace/`
- keep per-project memory, index, audit, history, and session state
- expose safe file, git, and configured OS command helpers

## Current Model

`workspace/` is a container for isolated projects:

```text
workspace/
  app1/
  app2/
  app3/
```

The active project controls the scope for:

- file reads and writes
- code indexing
- memory
- task history
- tool audit
- snapshots and exports
- git commands
- `/cmd cat ...`, `/cmd dir`, `/cmd pwd`, and other configured `/cmd` commands

The prompt shows the current project as:

```text
You (app1):
```

## Providers

- OpenRouter
- Hugging Face Inference Router
- Mistral AI

## Features

- modular agent runtime
- planner / executor / reviewer flow
- smart discovery with cache and ranking
- per-project isolation inside `workspace/`
- per-project session persistence
- per-project `AGENTS.md` guidance support
- code index and search
- git helpers scoped to the active project repo
- configurable `/cmd` commands from JSON
- optional Rich terminal panels and tables

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Create `.env`:

```env
OPENROUTER_API_KEY=your_openrouter_key
HF_TOKEN=your_huggingface_token
MISTRAL_API_KEY=your_mistral_api_key
HF_MODELS=Qwen/Qwen3-Coder-480B-A35B-Instruct,meta-llama/Llama-3.1-8B-Instruct
MISTRAL_MODELS=mistral-small-latest,codestral-latest
```

## Run

```bash
python main.py
```

## Important Files

- `.cmd_commands.json`: configured `/cmd` commands
- `workspace/<project>/.cmd_commands.json`: project-local `/cmd` overrides and additions
- `.model_discovery_cache.json`: discovery cache
- `.model_ranking.json`: route ranking stats
- `workspace/.active_project.json`: saved active project
- `workspace/<project>/.agent_session.json`: per-project session settings
- `workspace/<project>/AGENTS.md`: optional project-local guidance

## `/cmd` Configuration

Configured OS commands are loaded from:

- repo-level `.cmd_commands.json`
- active-project `workspace/<project>/.cmd_commands.json`

Project-local commands override repo-level commands with the same name.

Example:

```json
{
  "dir": "dir",
  "ls": "ls",
  "pwd": "pwd",
  "cat": "cat"
}
```

Examples:

```text
/cmdlist
/cmd pwd
/cmd dir
/cmd cat README.md
/cmdadd whoami whoami
/cmddel whoami
```

Notes:

- `/cmd` only runs commands present in `.cmd_commands.json`
- `/cmdadd` and `/cmddel` write to the active project's `.cmd_commands.json`
- `cat` paths are resolved inside the active project
- shell metacharacters are blocked
- subprocess-style commands still require confirmation

## Commands

### General

```text
/help [COMMAND]
/dashboard
/usage
/verbose LEVEL
/clear
/exit
```

### Projects

```text
/projects
/project NAME
/projectnew NAME
/projectclone SRC DEST
/projectinfo [NAME]
/projectrename OLD NEW
/projectdelete NAME
/projectpath
```

### Models

```text
/models
/model ROUTE
/provider MODE
/profiles
/profile NAME
/hfmodels
/addhfmodel MODEL
/removehfmodel MODEL
/mistralmodels
/addmistralmodel MODEL
/removemistralmodel MODEL
```

### Discovery

```text
/discover
/discoverfull
/discovercache
/cleardiscover
/resetmodels
/ranking
/resetranking
```

`/discoverfull` performs a full live scan without cache or early stop. OpenRouter is scanned across its fetched free-model catalog; Hugging Face is scanned across the configured HF candidate list; Mistral is scanned across the models available to the API key, or `.mistral_models` / `MISTRAL_MODELS` if provided.

### Automation

```text
/auto on|off
/smartauto on|off
/review on|off
/autorounds N
/tooliters N
/dryrun on|off
```

### Files And `/cmd`

```text
/snapshot NAME
/exportrepo NAME
/cmd NAME [ARGS]
/cmdlist
/cmdadd NAME COMMAND
/cmddel NAME
/path PATH
/readlines FILE
/index
/indexstats
/searchcode QUERY
```

### Agent Tasks

```text
/subagents
/asksubagent ROLE PROMPT [--file FILE] [--task ID] [--no-task] [--preview]
/explain FILE
/reviewfile FILE
/refactor FILE
/fix TEXT
/tests
```

`/asksubagent` includes the latest task context from the active project by default, and you can override it with `--task ID` or disable it with `--no-task`. The `worker` role accepts `--file FILE` for single-file work or `--scope PATH` for a bounded directory scope, and it returns a JSON patch payload that only applies inside that scope.

### Git

```text
/gitstatus
/gitfiles
/gitdiff
/gitdiffcached
/gitadd
/gitunstage
/gitlog [N]
/gitshow [REF]
/gitrestore
/gitrestore FILE
/gitcommitdry
/gitinit
/gitsafedir
/gitsafedir apply
/gitbranch NAME
/gitcommit MESSAGE
```

Git behavior:

- git commands only run when the active project has its own `.git`
- `/gitinit` initializes the active project as its own repository
- `/gitsafedir` shows the `git config --global --add safe.directory ...` fix for the active project
- `/gitsafedir apply` applies that fix after confirmation
- `/gitfiles` shows changed files in the active project
- `/gitdiffcached` shows the staged diff
- `/gitadd` stages active project changes
- `/gitunstage` unstages active project changes
- `/gitrestore FILE` restores tracked changes in one active-project file
- `/gitcommit` previews the active-project diff before confirmation
- `/gitcommit` stages and commits only the active project repo

### Memory And History

```text
/memory
/memoryclear
/memorynote TEXT
/cmdhistory
/history
/historyclear
/task ID
/audit
/auditclear
```

The app also keeps the last 50 user-entered commands in the active project's session file so they are available again in the next session. They are reloaded into the prompt history for the active project, and `/cmdhistory` shows them explicitly.

The startup/dashboard view also shows project-specific visibility details such as:

- whether the active project has its own git repo
- whether project-local `AGENTS.md` exists
- the number of configured `/cmd` commands
- the number of saved command-history entries
- whether prompt-history support is available

### Guidance

```text
/guidance
/reloadguidance
```

Guidance is loaded from:

- repo-level `AGENTS.md`
- `SKILL/**/SKILLS.md`
- active-project `workspace/<project>/AGENTS.md`

## Discovery And Ranking

The app stores route performance and discovery results in:

```text
.model_ranking.json
.model_discovery_cache.json
```

Discovery reporting includes:

- candidates scanned per provider
- working and failed counts
- failure reasons
- cache vs live scan status

## Testing

Run:

```bash
python -m unittest discover -s tests -v
```

The current test suite covers CLI dispatch, project isolation, git helpers, shell safety, discovery, guidance, memory/history, and `/cmd` config behavior.

Internally, the shell and git layers now use structured operation results while preserving the existing string-based CLI output. This keeps the current UX stable while making future error handling and reporting safer to extend.
