---
name: add-mcp-tool
description: Add a new MCP tool to metagit runtime with schema, dispatch, gating, and tests.
triggers:
  - "add mcp tool"
  - "tools/list"
  - "tools/call"
edges:
  - target: context/mcp-runtime.md
    condition: when implementing runtime method handlers, schemas, and dispatch logic
  - target: context/conventions.md
    condition: when validating guardrails and verify checklist compliance
  - target: patterns/debug-mcp-runtime.md
    condition: when framed message flow or tool calls produce protocol errors
last_updated: 2026-05-05
---

# Add MCP Tool

## Context
Load `context/mcp-runtime.md` first. The source of truth is `src/metagit/core/mcp/runtime.py` plus supporting services under `src/metagit/core/mcp/services/`.

## Steps
1. Define tool name and argument contract.
2. Add `inputSchema` entry to runtime `_tool_schemas`.
3. Ensure tool name is included in state-appropriate registry in `tool_registry.py`.
4. Implement dispatch branch in `_dispatch_tool` (or call a new dedicated service method).
5. Add tests in `tests/core/mcp/test_runtime.py` for list + call + invalid args.
6. Add/adjust integration tests if state-gating behavior changes.

## Gotchas
- If schema and dispatcher validation drift, clients may pass checks but fail at runtime.
- New tools must respect gate state; inactive state should not expose high-risk operations.
- Return content should be JSON-serializable and stable for agent consumption.

## Verify
- [ ] Tool is visible in `tools/list` only in intended states.
- [ ] `tools/call` succeeds with valid args and returns structured content.
- [ ] Invalid args map to `-32602` with `invalid_arguments` data.
- [ ] `task lint` and MCP test suite pass.

## Debug
- For missing tool in list: check `ToolRegistry` and state snapshot logic.
- For call rejection: inspect gate state and allowed tool set.
- For protocol mismatch: inspect framed read/write handling and JSON envelope fields.

## Update Scaffold
- [ ] Update `.mex/ROUTER.md` "Current Project State" if what's working/not built has changed
- [ ] Update any `.mex/context/` files that are now out of date
- [ ] If this is a new task type without a pattern, create one in `.mex/patterns/` and add to `INDEX.md`
