---
name: merge-orchestrator
description: Implementing or extending RFC-0011 merge orchestrator validators, CLI, MCP, events, and docs.
triggers:
  - "merge orchestrator"
  - "metagit merge"
  - "metagit_merge_"
  - "RFC-0011"
edges:
  - target: "../context/conventions.md"
    condition: when writing service, CLI, MCP, or tests
  - target: "merge-orchestrator-store.md"
    condition: when changing models, paths, JSON store, git_ops, or merge events
  - target: "add-cli-command.md"
    condition: when changing the Click command group
  - target: "add-mcp-tool.md"
    condition: when changing MCP schemas, registry, or dispatch
  - target: "modality-feature-registry.md"
    condition: when changing user-facing CLI/MCP/docs/skills parity
last_updated: 2026-07-09
---

# Merge Orchestrator

## Context

RFC-0011 spans core service behavior, local GitPython operations, CLI/MCP
adapters, context events, validators, docs, and modality parity. Keep business
logic in `metagit.core.merge`; adapters should validate input and return
`model_dump(mode="json")` shapes.

## Steps

1. Start with focused tests for the behavior being changed:
   - core service/store/git behavior under `tests/core/merge/`
   - CLI behavior under `tests/cli/commands/test_merge_cli.py`
   - MCP behavior under `tests/core/mcp/test_merge_tools.py`
2. Run the new test first and confirm the expected red state.
3. Keep Git mutation inside `git_ops.py`; keep orchestration in
   `MergeOrchestrator`; keep command execution in `validators.py`.
4. Preserve opt-in validators: default `merge.validators` is `[]`.
5. Preserve conflict safety: on conflict, abort the git merge and record ACL
   command hints only. Do not allocate branches, leases, worktrees, or claims.
6. For user-facing changes, update `scripts/modality-parity.yml`, docs markers,
   and bundled skill markers; regenerate the modality registry.
7. Update `CHANGELOG.md`, `.mex/ROUTER.md`, and RFC series docs when shipped
   behavior changes.

## Gotchas

- `merge_cmd.py` avoids the stdlib module name `merge` ambiguity.
- MCP tools are ACTIVE-gated in `ToolRegistry`; missing registry entries make
  calls fail before dispatch.
- `metagit_merge_*` tools should use the same `MergeOrchestrator` service as CLI.
- Validators run configured commands with `/bin/sh` from the repository path.
- `promote` merges the integration branch (`target_branch`) into the requested
  branch only after a successful validation gate.

## Verify

- [ ] `uv run pytest tests/core/merge`
- [ ] `uv run pytest tests/cli/commands/test_merge_cli.py`
- [ ] `uv run pytest tests/core/mcp/test_merge_tools.py`
- [ ] `uv run python scripts/check_modality_parity.py`
- [ ] `task qa:prepush`
- [ ] `task gitnexus:analyze`

## Debug

- If CLI commands cannot find merge records, check `--definition` and session
  root resolution through `resolve_acl_roots`.
- If MCP calls report "Tool not available", check `ToolRegistry` active tools.
- If conflicts leave `.git/MERGE_HEAD`, fix `git_ops.attempt_merge` before
  touching service/adapters.

## Update Scaffold

- [ ] Update `.mex/ROUTER.md` "Current Project State" when RFC-0011 scope changes.
- [ ] Update docs/skills/modalities for any user-facing behavior.
- [ ] Keep this pattern current with new RFC-0011 gotchas.
