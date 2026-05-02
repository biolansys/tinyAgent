# AGENTS.md

Rules for AI agents working in this repository:

- Work inside `workspace/` unless editing agent configuration.
- Use `/project` to switch to the active project before project-specific work.
- Inspect files before modifying them.
- Use small, reversible edits.
- Prefer line-based patches.
- Use `/edit FILE` for one-file changes and `/asksubagent worker` for scoped multi-file changes.
- Check `/gitstatus` before `/gitcommit`.
- Keep project-specific command aliases in `workspace/<project>/.cmd_commands.json`.
- Do not run destructive commands.
- Use `/snapshot` before large changes.
- Use `plan -> search -> review -> worker` for larger tasks when you want to split design, discovery, critique, and implementation.
- Use `worker` only with an explicit `--file FILE` or `--scope PATH`, and keep writes inside that boundary.
- Use direct app instructions for small one-file edits or quick questions; use subagents for multi-file or higher-risk work.
- Any new test script must be created under ./tests directory inside the project only.
- Do not create test scripts in the project root or other directories.
- If a test helper is needed, place it in ./tests directory inside the project (or a subfolder of ./tests).
- Create README.md at project creation time.
- Keep updating it as the app evolves.