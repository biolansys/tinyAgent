# AGENTS.md

Rules for AI agents working in this repository:

- Work inside `workspace/` unless editing agent configuration.
- Inspect files before modifying them.
- Use small, reversible edits.
- Create backups before overwriting files.
- Prefer line-based patches.
- Ask before shell commands.
- Do not run destructive commands.
- Use `/snapshot` before large changes.
