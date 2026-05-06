# Command Reference (Detailed)

This file is the canonical detailed reference for CLI commands.
It is intended to be consumed later by `/help` for rich per-command help output.

## General

- `/help [COMMAND]`  
  Shows grouped command list, or detailed help matches for one command token.
  Example: `/help /gitcommit`

- `/dashboard`  
  Prints startup/runtime summary including project context and selected routes.
  Example: `/dashboard`

- `/doctor`  
  Runs local diagnostics: directories, credentials presence, git binary/repo, routes, plugin load status.
  Example: `/doctor`

- `/smoketest`  
  Runs a quick readiness check bundle for the active project:
  - doctor output availability
  - plugin loader state
  - active project path
  - core command-map sanity
  Returns `PASS` or `WARN` with per-check details.
  Example: `/smoketest`

- `/releasecheck`  
  Runs one-step release readiness checks:
  - docs presence (`COMMAND_REFERENCE.md`)
  - command-doc consistency (`COMMANDS` vs command reference entries)
  - smoketest status
  - full unit test suite (`python -m unittest discover -s tests -v`)
  On `WARN`, automatically creates a CI artifact pack in `logs/releasecheck/` with:
  - `doctor.txt`
  - `smoketest.txt`
  - `releasecheck.txt`
  - key project logs/session/memory files when available
  Returns consolidated `PASS` or `WARN` report with details.
  Example: `/releasecheck`

- `/usage`  
  Prints token usage counters and route usage distribution for the current session.
  Example: `/usage`

- `/verbose LEVEL`  
  Sets verbosity level (`0..3`) affecting runtime and tool-call trace output.
  Example: `/verbose 2`

- `/temperature N`  
  Sets model temperature (`0.0..2.0`) for subsequent tasks.
  Example: `/temperature 0.2`

- `/clear`  
  Resets in-memory conversation messages for the main runtime.
  Example: `/clear`

- `/restart`  
  Restarts the application process with current CLI arguments.
  Example: `/restart`

- `/exit`  
  Exits the app loop.
  Example: `/exit`

## Models And Discovery

- `/models`  
  Lists currently selected provider routes in execution order.

- `/discover`  
  Smart discovery using cache/ranking/early-stop and applies ranked routes.

- `/discoverfull`  
  Full discovery without cache or early-stop.

- `/discovercache`  
  Shows discovery cache report.

- `/cleardiscover`  
  Clears discovery cache file/state.

- `/resetmodels`  
  Re-discovers and re-ranks routes, then stores session state.

- `/model ROUTE`  
  Forces single route for subsequent requests.
  Example: `/model openrouter::openrouter/free`

- `/provider MODE`  
  Sets provider mode (`auto|openrouter|huggingface|mistral`).

- `/profiles`  
  Lists built-in execution profiles.

- `/profile NAME`  
  Applies one profile (`fast|coding|debug|safe|openrouter|huggingface|mistral`).

- `/ranking`  
  Shows model ranking statistics.

- `/resetranking`  
  Clears ranking statistics.

- `/hfmodels`  
  Lists configured Hugging Face candidate models.

- `/addhfmodel MODEL`  
  Adds one Hugging Face model to config.

- `/removehfmodel MODEL`  
  Removes one Hugging Face model from config.

- `/mistralmodels`  
  Lists configured Mistral candidate models.

- `/addmistralmodel MODEL`  
  Adds one Mistral model to config.

- `/removemistralmodel MODEL`  
  Removes one Mistral model from config.

## Automation Controls

- `/auto on|off`  
  Enables/disables autonomous continuation behavior.

- `/smartauto on|off`  
  Enables/disables policy-based auto continuation gating.

- `/review on|off`  
  Enables/disables reviewer pass in task loop.

- `/autorounds N`  
  Sets max reviewer/fixer auto rounds.

- `/tooliters N`  
  Sets max tool iterations per plan step.

- `/dryrun on|off`  
  Enables/disables dry-run behavior for mutating tools.

## Projects

- `/projects`  
  Lists projects in `workspace/`, marking the active one.

- `/project NAME`  
  Switches active project and reloads project session/context.

- `/projectnew NAME [--template python-cli|tkinter|api]`  
  Creates and switches to project (with bootstrap + hooks), and optionally applies starter scaffolding.
  Examples:
  - `/projectnew myapp`
  - `/projectnew mycli --template python-cli`
  - `/projectnew mydesk --template tkinter`
  - `/projectnew myapi --template api`

- `/projectclone SRC DEST`  
  Clones one project folder to a new project and switches to it.

- `/projectinfo [NAME]`  
  Prints project metadata (files/dirs/size/git/session/guidance flags).

- `/projectrename OLD NEW`  
  Renames project after confirmation.

- `/projectdelete NAME`  
  Deletes project after confirmation, then updates active project.

- `/projectpath`  
  Prints active project absolute path.

## Guidance And Plugins

- `/guidance`  
  Prints aggregated guidance (repo + skill + project guidance files).

- `/reloadguidance`  
  Reloads runtime system guidance.

- `/plugins`  
  Prints loaded plugin commands/hooks and loader errors.

## File And Index Utilities

- `/snapshot NAME`  
  Creates ZIP snapshot for active project.

- `/exportrepo NAME`  
  Creates project export archive.

- `/path PATH`  
  Validates and normalizes active-project-relative path.

- `/readlines FILE`  
  Reads file with line numbers.

- `/index`  
  Builds/refreshes code index for active project.

- `/indexstats`  
  Shows code index statistics.

- `/searchcode QUERY`  
  Searches the code index.

## Configured OS Commands

- `/cmd NAME [ARGS]`  
  Runs one configured command mapping from repo/project command config.

- `/cmdlist`  
  Lists effective configured commands (project overrides included).

- `/cmdadd NAME COMMAND`  
  Adds/updates one project-local configured command entry.

- `/cmddel NAME`  
  Removes one project-local configured command entry.

- `/cmdhistory`  
  Prints persisted recent command history for active project.

## Agent And Subagent Tasks

- `/edit FILE [--instruction TEXT] [--preview]`  
  Runs bounded single-file edit loop with diff/confirmation flow.

- `/asksubagent ROLE PROMPT [--file FILE] [--task ID] [--no-task] [--preview]`  
  Runs specialist subagent; `worker` requires explicit ownership via `--file` or `--scope`.

- `/runplan [FILE]`  
  Executes markdown plan file containing `/asksubagent ...` lines only.  
  Default file is `RUNPLAN.md`. Always prompts for confirmation first.

- `/explain FILE`  
  Asks runtime to explain a file’s purpose/structure/dependencies/risks.

- `/reviewfile FILE`  
  Asks runtime to review one file for bugs/maintainability/security.

- `/refactor FILE`  
  Asks runtime for safe refactor suggestions on one file.

- `/fix TEXT`  
  Runs task flow to analyze and fix an error/traceback request.

- `/tests`  
  Runs task flow to detect safest project test command and execute/suggest it.

## Git Commands

- `/gitstatus`  
  Shows git status for active project repository.

- `/gitfiles`  
  Shows changed files in active project repo.

- `/gitdiff`  
  Shows unstaged diff.

- `/gitdiffcached`  
  Shows staged diff.

- `/gitadd`  
  Stages changes (confirmation-protected).

- `/gitunstage`  
  Unstages changes (confirmation-protected).

- `/gitlog [N]`  
  Shows recent commit log (optional limit).

- `/gitshow [REF]`  
  Shows one revision summary (default `HEAD`).

- `/gitrestore`  
  Restores tracked changes in active project (confirmation-protected).

- `/gitrestore FILE`  
  Restores tracked changes in one file (confirmation-protected).

- `/gitcommitdry`  
  Previews what `/gitcommit` would include.

- `/gitinit`  
  Initializes git repository in active project root (confirmation-protected).

- `/gitsafedir`  
  Shows `safe.directory` fix command for active project.

- `/gitsafedir apply`  
  Applies `safe.directory` fix globally (confirmation-protected).

- `/gitbranch NAME`  
  Creates and switches branch (confirmation-protected).

- `/gitcommit MESSAGE`  
  Stages and commits active project changes (confirmation-protected).

## History, Runs, Audit, Memory

- `/history`  
  Shows task history report.

- `/historyclear`  
  Clears task history log for active project.

- `/task ID`  
  Shows details for one task.

- `/taskresume ID`  
  Resumes checkpointed task execution.

- `/taskretry ID [--tooliters N] [--provider MODE] [--review on|off] [--safe|--force]`  
  Retries saved task input with temporary runtime overrides.

- `/runs`  
  Lists stored checkpoints.

- `/run ID`  
  Prints raw checkpoint payload for one run.

- `/runclear ID`  
  Deletes one checkpoint.

- `/runclearall`  
  Deletes all checkpoints for active project.

- `/audit`  
  Shows recent tool audit entries.

- `/auditclear`  
  Clears tool audit log.

- `/memory`  
  Prints project memory document.

- `/memoryclear`  
  Clears project memory document.

- `/memorynote TEXT`  
  Appends one note to project memory.

## Notes For Future `/help` Integration

- Parse this file as command blocks keyed by exact command signature.
- Resolve user queries by:
  1. exact signature match
  2. base command token match
  3. fuzzy contains fallback
- Render command details with: syntax, behavior, example, and safety notes.
