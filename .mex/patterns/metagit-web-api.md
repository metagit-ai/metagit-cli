# Metagit local web API (`metagit web serve`)

## Models

- Pydantic shapes for the localhost web UI live in `src/metagit/core/web/models.py`.
- Extend that module for new request/response types; keep CLI and HTTP handlers thin and delegate validation to these models.

## Server wiring

- `build_web_server(root, appconfig_path, host, port)` in `src/metagit/core/web/server.py` — `ThreadingHTTPServer` + `BaseHTTPRequestHandler`, same JSON helper pattern as `metagit.core.api.server`.
- Config routes live in `ConfigWebHandler` (`src/metagit/core/web/config_handler.py`): GET/PATCH `/v3/config/{metagit|appconfig}[/tree]`, POST `/v3/config/validate`.
- Ops routes live in `OpsWebHandler` (`src/metagit/core/web/ops_handler.py`): POST `/v3/ops/health`, `/v3/ops/prune/preview`, `/v3/ops/prune`, `/v3/ops/sync`; GET `/v3/ops/sync/{job_id}`; GET `/v3/ops/sync/{job_id}/events` (SSE). Module-level `SyncJobStore` tracks async sync jobs.

## When adding routes later

- Extend `ConfigWebHandler` / `OpsWebHandler` or add sibling handlers; register in `server.py` `Handler._dispatch` (SSE: match path before JSON dispatch).
- Run `task qa:prepush` before hand-off.
