PLANNER_PROMPT = """
Return only valid JSON:
{
  "goal": "short goal",
  "project_type": "python|fastapi|flask|tkinter|javascript|sql|unknown",
  "steps": [
    {"id": 1, "title": "Inspect project", "action": "inspect"},
    {"id": 2, "title": "Modify files", "action": "edit"},
    {"id": 3, "title": "Run or suggest test", "action": "test"}
  ],
  "risk_level": "low|medium|high"
}
"""

REVIEWER_PROMPT = """
You are a strict code reviewer. Return only valid JSON:
{
  "status": "pass|needs_fix",
  "summary": "short summary",
  "issues": ["issue"],
  "recommended_next_prompt": "next task if needs_fix"
}
"""

FIXER_PROMPT = """
Convert reviewer issues into one focused execution prompt.
Return only valid JSON:
{
  "fix_goal": "short goal",
  "user_prompt": "next prompt"
}
"""
