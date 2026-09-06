---
name: component-claims
description: Optional --component on claim declare/check (RFC-0030).
triggers:
  - "claim --component"
  - "FileClaim.component"
  - "RFC-0030"
  - "component claim"
edges:
  - target: "component-resolution.md"
    condition: when ComponentResolver.get or project/repo/component identity is involved
  - target: "agent-coordination-acl.md"
    condition: when changing claim store, overlap, or ACL events
  - target: "add-cli-command.md"
    condition: when changing metagit claim declare|check flags
  - target: "add-mcp-tool.md"
    condition: when changing metagit_claim_declare / metagit_claim_check schema
last_updated: 2026-09-06
---

# Component claims (RFC-0030)

## Context

Design: `docs/superpowers/specs/2026-09-06-rfc-0030-component-ownership-design.md`.
Depends on RFC-0027 `ComponentResolver.get`.

Service: `src/metagit/core/coordination/claim_service.py`.
Model: `FileClaim.component` (component **name**, not three-segment id).
CLI: `src/metagit/cli/commands/claim.py`.
MCP: `metagit_claim_declare` / `metagit_claim_check` in `runtime.py`.
Tests: `tests/core/coordination/test_coordination_services.py`.

Do not invent a `component_claim` modality — extend `acl_claim`.
Do not import `catalog` or `resolve` from `metagit.core.component.__init__`.

## Steps

1. Put expansion/lookup in `ClaimService._resolve_claim_patterns`. CLI/MCP stay thin.
2. When `component` is set, require `config` and a two-segment `repository` (`project/repo`). Resolve via `ComponentResolver.get(config, f"{project}/{repo}/{component}")`.
3. Empty patterns + component → `[f"{path}/**"]` except path `.` → `["**"]`. Explicit patterns stay as given.
4. `check()` uses the same expansion. Overlap stays repository + patterns.
5. CLI `--pattern` is optional. No `--component` and no patterns → error. Load `MetagitConfig` from `--definition` only when `--component` is set.
6. MCP: `component` optional; `patterns` may be empty when `component` is set.

## Gotchas

- `FileClaim.component` is the name (`web`), not `platform/core/web`.
- Unknown component is `ValueError`, not a whole-repo claim.
- Two agents on `web` vs `api` do not conflict when expanded paths do not overlap.
- Same component still conflicts under `--strict`.
- Claims without `--component` still require at least one pattern.

## Verify

- [ ] `uv run pytest tests/core/coordination/test_coordination_services.py -q`
- [ ] `zsh ./scripts/prepush-gate.zsh` if `task qa:prepush` mise shim fails
