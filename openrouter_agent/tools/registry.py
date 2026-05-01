import math, json
from .files import (
    file_tree, read_text_file, write_text_file, replace_in_file, patch_lines,
    search_files, read_file_with_line_numbers, snapshot, export_repo, validate_path
)
from .shell import run_shell_command
from ..memory import remember, read_memory_text
from ..audit import audit_report, history_report, task_detail
from ..gittools import git_status, git_diff
from ..indexer import build_code_index, search_code_index, index_stats, explain_index_file

def calculator(expression):
    allowed = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "pi": math.pi, "e": math.e, "abs": abs, "round": round, "min": min, "max": max}
    try:
        return str(eval(expression, {"__builtins__": {}}, allowed))
    except Exception as e:
        return f"Calculator error: {e}"

def create_requirements(packages):
    lines = [p.strip() for p in packages.split(",") if p.strip()]
    return write_text_file("requirements.txt", "\n".join(lines) + "\n")

def tool_schema(name, description, properties, required=None):
    return {"type": "function", "function": {"name": name, "description": description, "parameters": {"type": "object", "properties": properties, "required": required or []}}}

TOOLS = {
    "calculator": calculator,
    "file_tree": file_tree,
    "read_text_file": read_text_file,
    "read_file_with_line_numbers": read_file_with_line_numbers,
    "write_text_file": write_text_file,
    "replace_in_file": replace_in_file,
    "patch_lines": patch_lines,
    "search_files": search_files,
    "create_requirements": create_requirements,
    "run_shell_command": run_shell_command,
    "remember_note": remember,
    "read_memory": read_memory_text,
    "create_project_snapshot": snapshot,
    "export_repo": export_repo,
    "validate_agent_path": validate_path,
    "build_code_index": build_code_index,
    "search_code_index": search_code_index,
    "index_stats": index_stats,
    "explain_index_file": explain_index_file,
    "audit_report": audit_report,
    "history_report": history_report,
    "task_detail": task_detail,
    "git_status": git_status,
    "git_diff": git_diff,
}

SCHEMAS = [
    tool_schema("file_tree", "Show active project file tree.", {"path": {"type": "string"}, "max_depth": {"type": "integer"}}, ["path"]),
    tool_schema("search_files", "Search text inside active project files.", {"query": {"type": "string"}, "path": {"type": "string"}, "extensions": {"type": "string"}}, ["query"]),
    tool_schema("read_text_file", "Read active project file.", {"path": {"type": "string"}}, ["path"]),
    tool_schema("read_file_with_line_numbers", "Read active project file with line numbers.", {"path": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}}, ["path"]),
    tool_schema("write_text_file", "Write active project file.", {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    tool_schema("replace_in_file", "Replace exact text in active project file.", {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, ["path", "old_text", "new_text"]),
    tool_schema("patch_lines", "Patch line range in active project file.", {"path": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}, "new_text": {"type": "string"}}, ["path", "start_line", "end_line", "new_text"]),
    tool_schema("create_requirements", "Create requirements.txt.", {"packages": {"type": "string"}}, ["packages"]),
    tool_schema("run_shell_command", "Run safe shell command with confirmation.", {"command": {"type": "string"}}, ["command"]),
    tool_schema("remember_note", "Save project note.", {"note": {"type": "string"}, "project_type": {"type": "string"}}, ["note"]),
    tool_schema("read_memory", "Read project memory.", {}, []),
    tool_schema("create_project_snapshot", "Create active project zip snapshot.", {"name": {"type": "string"}}, []),
    tool_schema("export_repo", "Create active project repository zip.", {"name": {"type": "string"}}, []),
    tool_schema("validate_agent_path", "Validate active project path normalization.", {"path": {"type": "string"}}, ["path"]),
    tool_schema("build_code_index", "Build or refresh workspace code index.", {"path": {"type": "string"}}, []),
    tool_schema("search_code_index", "Search the code index.", {"query": {"type": "string"}, "limit": {"type": "integer"}}, ["query"]),
    tool_schema("index_stats", "Show code index stats.", {}, []),
    tool_schema("explain_index_file", "Show indexed metadata for one file.", {"path": {"type": "string"}}, ["path"]),
    tool_schema("audit_report", "Show recent tool audit log.", {"limit": {"type": "integer"}}, []),
    tool_schema("history_report", "Show recent task history.", {"limit": {"type": "integer"}}, []),
    tool_schema("task_detail", "Show detailed history for a task id.", {"task_id": {"type": "string"}}, ["task_id"]),
    tool_schema("git_status", "Show git status.", {}, []),
    tool_schema("git_diff", "Show git diff.", {}, []),
]
