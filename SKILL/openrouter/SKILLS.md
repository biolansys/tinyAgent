# Provider Skill

Use provider-aware routing and discovery rules for this app.

- Prefer the active provider mode for the current project.
- Use `/discover` for cached smart discovery and `/discoverfull` for a full candidate scan.
- Verify new provider routes with `/models` and `/discovercache`.
- Keep provider-specific model lists in the matching config file.
- Use the provider that best matches the task, but keep fallbacks enabled.
