# Metagit local web API (`metagit web serve`)

## Models

- Pydantic shapes for the localhost web UI live in `src/metagit/core/web/models.py`.
- Extend that module for new request/response types; keep CLI and HTTP handlers thin and delegate validation to these models.

## Server wiring

- `build_web_server(root, appconfig_path, host, port)` in `src/metagit/core/web/server.py` — `ThreadingHTTPServer` + `BaseHTTPRequestHandler`, same JSON helper pattern as `metagit.core.api.server`.
- Config routes live in `ConfigWebHandler` (`src/metagit/core/web/config_handler.py`): GET/PATCH `/v3/config/{metagit|appconfig}[/tree]`, POST `/v3/config/validate`.

## When adding routes later

- Extend `ConfigWebHandler` or add sibling handlers; register methods in `server.py` `Handler._dispatch`.
- Run `task qa:prepush` before hand-off.
