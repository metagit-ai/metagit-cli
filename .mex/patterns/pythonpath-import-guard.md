---
name: pythonpath-import-guard
description: Keep metagit's site-packages first on sys.path so caller PYTHONPATH cannot shadow bundled deps.
edges:
  - target: ../context/conventions.md
    condition: when changing package import bootstrap
last_updated: 2026-07-09
---

# PYTHONPATH import guard

## When to use

Import crashes like `ModuleNotFoundError: No module named pydantic_core._pydantic_core` when an embedding host (Hermes, etc.) exports `PYTHONPATH` pointing at its own venv.

## Do

1. Keep the guard as the **first executable code** in `src/metagit/__init__.py` (before any third-party imports).
2. Prepend `sysconfig.get_paths()['purelib']` to `sys.path`; do **not** clear or rewrite the `PYTHONPATH` env var; do **not** require `python -E`.
3. Keep `tests/test_pythonpath_guard.py` green (hostile decoy `pydantic` on `PYTHONPATH`).

## Don't

- Don't move pydantic imports earlier than the guard.
- Don't delete caller `PYTHONPATH` — legitimate path use must still work after our purelib.

## Verify

```bash
uv run pytest tests/test_pythonpath_guard.py -q
```
