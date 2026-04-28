# Safety Skill

Safety rules for local agent execution.

## File Safety

- Restrict file operations to the workspace.
- Ignore risky or noisy directories:
  - `.git`
  - `venv`
  - `.venv`
  - `node_modules`
  - `dist`
  - `build`
  - `__pycache__`

## Edit Safety

- Show diffs before edits.
- Create backups before overwriting.
- Prefer line-based patches.
- Create snapshots before large refactors.

## Command Safety

Only allow safe development commands such as:

- `python`
- `python -m pytest`
- `python -m pip`
- `git status`
- `git diff`
- `dir`
- `ls`

Block destructive or system-level commands.
