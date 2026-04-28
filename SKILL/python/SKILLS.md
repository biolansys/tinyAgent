# Python Skill

Guidance for Python development tasks.

## Coding Style

- Prefer clear, simple Python.
- Use standard library when possible.
- Add helpful error handling.
- Keep functions small and testable.
- Avoid unnecessary dependencies.

## Debugging Workflow

1. Read the traceback carefully.
2. Identify the exact file and line.
3. Inspect the relevant code.
4. Apply a minimal fix.
5. Run a safe command such as:
   - `python script.py`
   - `python -m pytest`

## Dependency Workflow

If dependencies are needed:

1. Create or update `requirements.txt`.
2. Use:
   - `python -m pip install -r requirements.txt`

## GUI Notes

For Tkinter projects:

- Keep UI updates on the main thread.
- Avoid blocking the UI loop.
- Use `after()` for scheduled UI updates.
