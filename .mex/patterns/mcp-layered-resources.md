---
name: mcp-layered-resources
description: Add or extend Metagit MCP layered resources (catalog, map, prompts, scoped project/repo URIs).
triggers:
  - "mcp resource"
  - "resources/list"
  - "resources/read"
  - "metagit://catalog"
edges:
  - target: context/mcp-runtime.md
    condition: when implementing runtime handlers or gate exposure
  - target: patterns/add-mcp-tool.md
    condition: when a new capability also needs a mutating tool
last_updated: 2026-06-30
---

# MCP layered resources

## Context

Load `context/mcp-runtime.md` and `docs/reference/mcp-layered-resources-spec.md`.

Implementation: `resource_catalog.py` (URI registry), `resource_service.py` (payload assembly), `resources.py` (runtime facade), wired in `runtime.py` `_handle_resources_list` / `_handle_resources_read`.

## Steps

1. Add static or dynamic pattern to `resource_catalog.py` (`ResourceDescriptor` or `DynamicUriPattern`).
2. Implement read branch in `ResourceService.read()` reusing existing core services.
3. Choose MIME type: JSON (`application/json`) for facts; `text/plain` for prompts.
4. Ensure read path is **idempotent** — no session boundary, objective, or approval writes.
5. Add tests: `test_resource_catalog.py`, `test_resource_service.py`, `test_runtime.py` resources/list + read.
6. Update spec phase table, `metagit-mcp-resources` skill, `docs/agents.md`.

## Verify

- [ ] `resources/list` includes new static URIs when gate allows.
- [ ] Dynamic URIs documented in `metagit://catalog` patterns.
- [ ] `resources/read` returns correct `mimeType`.
- [ ] No mutation of `.metagit/sessions/` on read.
