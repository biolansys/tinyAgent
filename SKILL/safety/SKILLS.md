# Safety Skill

Keep agent actions constrained and explicit.

- Restrict file changes to the active project unless editing agent configuration.
- Do not use destructive commands.
- Confirm mutating shell and git actions when the app asks for confirmation.
- Use configured `/cmd` entries for trusted command aliases.
- Keep subagent writes inside the declared `--file` or `--scope`.
- Prefer read-only inspection before mutation.
