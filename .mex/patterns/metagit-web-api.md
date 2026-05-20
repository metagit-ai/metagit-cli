# Metagit local web API (`metagit web serve`)

## Models

- Pydantic shapes for the localhost web UI live in `src/metagit/core/web/models.py`.
- Extend that module for new request/response types; keep CLI and HTTP handlers thin and delegate validation to these models.

## When adding routes later

- Mirror existing `metagit.core.api` patterns for FastAPI/Starlette wiring if the stack matches.
- Run `task qa:prepush` before hand-off.
