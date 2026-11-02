# Agents



## Constraints
- Do not make unrelated refactors or formatting-only edits.
- Do not run destructive git operations.
- Prefer existing project tasks and scripts over ad-hoc commands.
- Keep changes small and aligned with existing code patterns.
- Keep business logic focused on the happy path, but implement required authentication, authorization, validation, and token-refresh handling.
- Assume code works in normal conditions instead of adding handling for rare expected failures.

## Project Setup
- Python version: 3.14. Don't use newer syntax.
- Dependency management: `uv` and `pyproject.toml`. Never use `pip`
  or a `requirements.txt` file.
- Add a dependency with `uv add <package>`. Never use `uv pip`
  for dependencies.

## Coding conventions
 - Prefer f-strings over `str.format()` or `%` formatting.

 ## Frontend Architecture
 - This is now just a script 
 - Text for users must be in danish.