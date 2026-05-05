---
name: debug-mcp-runtime
description: Diagnose MCP runtime failures across framing, initialize capabilities, tool dispatch, and resource reads.
triggers:
  - "mcp error"
  - "tools/call failed"
  - "resources/read failed"
  - "stdio framing"
edges:
  - target: context/mcp-runtime.md
    condition: when tracing runtime internals and protocol method handling
  - target: context/architecture.md
    condition: when failure source may be outside runtime (service/config layer)
  - target: patterns/add-mcp-tool.md
    condition: when bug appears while adding/changing tool schemas or dispatch behavior
last_updated: 2026-05-05
---

# Debug MCP Runtime

## Context
Primary files: `src/metagit/core/mcp/runtime.py`, `tool_registry.py`, gate/root resolver, and MCP service modules. Primary tests: `tests/core/mcp/test_runtime.py` and MCP integration tests.

## Steps
1. Reproduce with smallest path first (`metagit mcp serve --status-once` for gate snapshot).
2. Check gate state and allowed tool set before debugging individual tool behavior.
3. Validate request envelope fields (`jsonrpc`, `id`, `method`, `params`) and framed transport boundaries.
4. Run focused runtime tests, then full MCP suite.
5. If method-specific failure persists, add/adjust regression tests before patching.

## Gotchas
- Mistaking inactive-gate tool denial for runtime logic failure.
- Schema/dispatcher mismatch causing valid-looking requests to fail.
- Framing bugs can masquerade as random parse/protocol errors.

## Verify
- [ ] Runtime methods (`initialize`, `tools/list`, `tools/call`, `resources/*`) pass tests.
- [ ] Invalid arguments consistently return `-32602`.
- [ ] Sampling capability detection reflects initialize input.
- [ ] MCP suite and lint pass after fix.

## Debug
- Use `tests/core/mcp/test_runtime.py` as first failure boundary.
- For tool visibility bugs, inspect `ToolRegistry.list_tools` with active/inactive statuses.
- For resource failures, inspect `ResourcePublisher` payload path and `uri` handling.

## Update Scaffold
- [ ] Update `.mex/ROUTER.md` "Current Project State" if what's working/not built has changed
- [ ] Update any `.mex/context/` files that are now out of date
- [ ] If this is a new task type without a pattern, create one in `.mex/patterns/` and add to `INDEX.md`
