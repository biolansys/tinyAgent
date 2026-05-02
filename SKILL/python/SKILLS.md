# Python Skill

Use Python changes that fit the repo's workflow and safety model.

- Prefer `apply_patch` for code edits.
- Keep changes small and reversible.
- Add or update tests when behavior changes.
- Use the existing test suite shape in `tests/`.
- Prefer safe commands such as `python -m unittest discover -s tests -v`.
- Keep dependencies minimal unless a feature clearly needs one.
