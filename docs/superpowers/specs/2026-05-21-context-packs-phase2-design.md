# Context Packs Phase 2 — Design Spec

**Date:** 2026-05-21  
**Status:** Approved  
**Depends on:** Phase 1 (T0/T1 context packs)

## Scope

1. **T2 session digest** — changes since last session (git + manifest)
2. **Objectives** — durable human/agent task state (CLI + MCP + Web API)
3. **Approval queue** — pending mutating ops awaiting human OK (CLI + MCP + Web API)
4. **Repomix context profiles** — token-budgeted repo snapshots by profile

## T2 Session Digest

- `WorkspaceSessionMeta.last_session_at` ISO timestamp
- `SessionStore.touch_session()` updates on context pack / session-start
- `SessionDigestService.build()`:
  - Per existing clone: commit count + top 3 subjects since `since`
  - Manifest: `config_changed` if `.metagit.yml` mtime > since
  - Active objective id (if any)
- `ContextPackResult.tier` extends to `0|1|2`; tier 2 = tier 1 + `digest`

## Objectives

Stored at `{workspace_root}/.metagit/sessions/objectives.json`.

```yaml
objectives:
  - id: fix-auth
    status: in_progress  # pending|in_progress|done|cancelled
    title: Fix auth regression
    repos: [platform/api]
    acceptance: Optional str
    human_notes: Optional str
    agent_notes: Optional str
    created_at, updated_at
```

- One `in_progress` objective recommended; multiple allowed
- CLI: `metagit context objective list|get|set|complete|cancel`
- MCP: `metagit_objective_list`, `metagit_objective_upsert`
- Web: `GET/POST /v3/ops/objectives`, `PATCH /v3/ops/objectives/{id}`

## Approval Queue

Stored at `{workspace_root}/.metagit/approvals/pending.json`.

```yaml
requests:
  - id: uuid
    action: repo_sync|catalog_repo_add|...
    status: pending|approved|denied
    requested_by: agent|human
    payload: dict
    created_at, resolved_at, resolver_note
```

- MCP: `metagit_approval_request`, `metagit_approval_list`, `metagit_approval_resolve`
- CLI: `metagit context approval list|approve|deny`
- Web: `GET /v3/ops/approvals`, `POST /v3/ops/approvals/{id}/resolve`

## Repomix Profiles

Profiles in `src/metagit/data/context_profiles.yaml`:

| Profile | Includes |
|---------|----------|
| bugfix-local | src/, tests/, pyproject.toml, schemas/ |
| config-edit | .metagit.yml, metagit.config.yaml, schemas/ |
| cross-repo-impact | manifest graph section, schemas/, docs/reference/ |

- `metagit context repomix --profile NAME --project P --repo R [--output PATH]`
- `task repomix:profile PROFILE=bugfix-local`

## Success criteria

- `metagit context pack --tier 2 --json` includes digest
- Objective CRUD round-trip via CLI and MCP
- Approval request → resolve changes status
- Repomix profile runs without full-repo dump
- `task qa:prepush` passes
