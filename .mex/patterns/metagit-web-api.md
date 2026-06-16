# Metagit local web API (`metagit web serve`)

## Models

- Pydantic shapes for the localhost web UI live in `src/metagit/core/web/models.py`.
- Extend that module for new request/response types; keep CLI and HTTP handlers thin and delegate validation to these models.

## Server wiring

- `build_web_server(root, appconfig_path, host, port)` in `src/metagit/core/web/server.py` — `ThreadingHTTPServer` + `BaseHTTPRequestHandler`, same JSON helper pattern as `metagit.core.api.server`.
- Static assets: `StaticWebHandler` (`src/metagit/core/web/static_handler.py`) serves `DATA_PATH/web/`; SPA fallback for non-API GET paths.
- GET dispatch order: static (non-API) → v2 catalog → v2 layout → v3 config → v3 ops → 404 JSON for unknown `/v*`.
- POST/DELETE/PATCH: layout, catalog, config, ops (no static).
- Config routes live in `ConfigWebHandler` (`src/metagit/core/web/config_handler.py`): GET/PATCH `/v3/config/{metagit|appconfig}[/tree]`, POST `/v3/config/validate`.
- PATCH applies batched `ConfigOperation` list via `SchemaTreeService.apply_operations`; each request reloads from disk then applies all ops — the SPA must send **cumulative** pending ops (`mergePendingOp` in `web/src/components/SchemaTree.tsx`), not only the latest mutation.
- REMOVE on list paths uses `_navigate_parent(..., mutate=True)` so null/missing parents (e.g. `workspace.projects` before save) are materialized as `[]` instead of raising `TypeError`.
- Ops routes live in `OpsWebHandler` (`src/metagit/core/web/ops_handler.py`): POST `/v3/ops/health`, `/v3/ops/prune/preview`, `/v3/ops/prune`, `/v3/ops/sync`, `/v3/ops/source-sync`; GET `/v3/ops/sync/{job_id}`; GET `/v3/ops/approvals`; POST `/v3/ops/approvals/{id}/resolve`; GET `/v3/ops/sync/{job_id}/events` (SSE). Approval resolve uses `ApprovalResolveOrchestrator` (same as CLI). Module-level `SyncJobStore` tracks async sync jobs.

## When adding routes later

- Extend `ConfigWebHandler` / `OpsWebHandler` or add sibling handlers; register in `server.py` `Handler._dispatch` (SSE: match path before JSON dispatch).
- Run `task qa:prepush` before hand-off.
