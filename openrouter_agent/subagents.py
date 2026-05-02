"""Subagent helpers."""

from __future__ import annotations

import json
from typing import Any

from .audit import task_context as load_task_context


SUBAGENT_ROLES = ("plan", "review", "search", "worker")

SUBAGENT_SYSTEM_PROMPTS = {
    "plan": (
        "You are a read-only planning subagent.\n"
        "Give a concise, ordered plan.\n"
        "Do not use tools, do not modify files, and do not claim to have executed actions."
    ),
    "review": (
        "You are a read-only code review subagent.\n"
        "Focus on correctness, regressions, missing tests, and safety.\n"
        "Do not use tools, do not modify files, and do not claim to have executed actions."
    ),
    "search": (
        "You are a read-only search subagent.\n"
        "Suggest likely files, symbols, or query terms to inspect.\n"
        "Do not use tools, do not modify files, and do not claim to have executed actions."
    ),
    "worker": (
        "You are a write-capable worker subagent.\n"
        "You may modify only the explicitly provided ownership scope in the task context.\n"
        "Return one JSON object only, without markdown fences or explanation.\n"
        "The JSON must have: scope, summary, patches.\n"
        "patches must be a list of objects with target_file, start_line, end_line, and new_text.\n"
        "For brand-new files, use start_line=0 and end_line=0 and provide the full file contents in new_text.\n"
        "The runner will infer file creation when the target does not exist.\n"
        "Use 1-based inclusive line numbers against the provided file contents for existing files.\n"
        "Do not change any other file and do not claim to have used tools."
    ),
}

SUBAGENT_ROLE_CONTEXT = {
    "plan": "Focus on the current task request, the checkpoint phase, and a concrete execution plan.",
    "review": "Focus on correctness, regressions, missing tests, and safety for the current task.",
    "search": "Focus on likely files, symbols, queries, and follow-up inspection steps for the current task.",
    "worker": "Focus on the explicit ownership scope and produce valid patches only inside it.",
}


def normalize_subagent_role(role: Any) -> str:
    text = str(role or "").strip().lower()
    if text not in SUBAGENT_ROLES:
        allowed = ", ".join(SUBAGENT_ROLES)
        raise ValueError(f"Unsupported subagent role: {role!r}. Expected one of: {allowed}")
    return text


def normalize_subagent_context(context: Any) -> str | None:
    if context is None:
        return None
    if isinstance(context, str):
        text = context.strip()
        return text or None
    if isinstance(context, (dict, list, tuple)):
        return json.dumps(context, indent=2, ensure_ascii=False, sort_keys=True)
    text = str(context).strip()
    return text or None


def build_subagent_context(
    state: Any,
    role: str,
    task_id: Any = None,
    context: Any = None,
    include_task_context: bool = True,
) -> dict[str, Any]:
    normalized_role = normalize_subagent_role(role)
    payload: dict[str, Any] = {
        "active_project": str(getattr(state, "active_project", "") or "").strip(),
        "provider_mode": str(getattr(state, "provider_mode", "") or "").strip(),
        "routes": list(getattr(state, "routes", []) or []),
        "role": normalized_role,
        "role_focus": SUBAGENT_ROLE_CONTEXT[normalized_role],
    }
    if context is not None:
        payload["context"] = context
    if include_task_context:
        task_data = load_task_context(task_id)
        if task_data:
            payload["task"] = task_data
    return payload


def build_subagent_messages(state: Any, role: str, prompt: str, context: Any = None, task_context: Any = None) -> list[dict[str, str]]:
    normalized_role = normalize_subagent_role(role)
    prompt_text = str(prompt or "").strip()
    if not prompt_text:
        raise ValueError("Subagent prompt must not be empty")

    context_text = normalize_subagent_context(context)
    task_context_text = normalize_subagent_context(task_context)
    project = str(getattr(state, "active_project", "") or "").strip()
    provider_mode = str(getattr(state, "provider_mode", "") or "").strip()

    user_sections = [f"Role: {normalized_role}", f"Request: {prompt_text}"]
    if project:
        user_sections.append(f"Active project: {project}")
    if provider_mode:
        user_sections.append(f"Provider mode: {provider_mode}")
    user_sections.append(f"Role focus: {SUBAGENT_ROLE_CONTEXT[normalized_role]}")
    if normalized_role == "worker" and isinstance(context, dict):
        target_file = str(context.get("target_file", "") or "").strip()
        scope_path = str(context.get("scope_path", "") or "").strip()
        current_content = context.get("current_content")
        current_content_with_line_numbers = context.get("current_content_with_line_numbers")
        ownership = str(context.get("ownership", "") or "").strip()
        if target_file:
            user_sections.append(f"Target file: {target_file}")
        if scope_path:
            user_sections.append(f"Scope: {scope_path}")
        if ownership:
            user_sections.append(f"Ownership:\n{ownership}")
        if current_content_with_line_numbers is not None:
            user_sections.append(f"Current file with line numbers:\n{str(current_content_with_line_numbers)}")
        if current_content is not None:
            user_sections.append(f"Current file contents:\n{str(current_content)}")
    if task_context_text:
        user_sections.append(f"Task context:\n{task_context_text}")
    if context_text and not (normalized_role == "worker" and isinstance(context, dict)):
        user_sections.append(f"Context:\n{context_text}")

    return [
        {"role": "system", "content": SUBAGENT_SYSTEM_PROMPTS[normalized_role]},
        {"role": "user", "content": "\n\n".join(user_sections)},
    ]


def _extract_message_content(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Subagent response missing choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if content is None:
        return ""
    return str(content)


def run_subagent(client: Any, state: Any, role: Any, prompt: Any, context: Any = None, task_context: Any = None) -> dict[str, Any]:
    normalized_role = normalize_subagent_role(role)
    messages = build_subagent_messages(state, normalized_role, prompt, context=context, task_context=task_context)
    data = client.chat(messages, tools=None, force_no_tools=True)
    content = _extract_message_content(data)
    return {
        "role": normalized_role,
        "prompt": str(prompt).strip(),
        "context": normalize_subagent_context(context),
        "task_context": normalize_subagent_context(task_context),
        "messages": messages,
        "content": content,
        "route": data.get("_route"),
        "provider": data.get("_provider"),
        "model": data.get("_model"),
        "tools_enabled": bool(data.get("_tools_enabled", False)),
        "raw": data,
    }


__all__ = [
    "SUBAGENT_ROLES",
    "SUBAGENT_SYSTEM_PROMPTS",
    "build_subagent_messages",
    "build_subagent_context",
    "normalize_subagent_context",
    "normalize_subagent_role",
    "run_subagent",
]
