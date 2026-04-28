# OpenRouter Skill

Guidance for using OpenRouter in this coding agent.

## Model Selection

- Prefer free working models discovered at startup.
- Prefer tool-capable models for agent mode.
- Fall back to chat-only models if tool calls fail.
- Cache model discovery results to reduce startup requests.

## API Behavior

- Validate every response before reading `choices`.
- Handle `error` responses gracefully.
- Retry with another model if one fails.
- Use low temperature for coding tasks.

## Tool Calling

When tools are enabled:

- Use tools only when useful.
- Do not assume file contents.
- Read files before editing.
- Use patch tools for targeted edits.
