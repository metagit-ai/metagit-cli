# RFC-0011 Merge Orchestrator & Conflict Resolution — Implementation Plan

> **For agentic workers:** Expand into bite-sized TDD steps when the RFC-0011 MR starts.

**Goal:** Enqueue and attempt merges of agent branches into integration branches, record conflicts/results, run opt-in validators, and emit merge events — without becoming a hosted CI system.

**Architecture:** `src/metagit/core/merge/` with queue store, GitPython merge attempts in temp/worktree-safe flows, conflict records, pluggable validator commands from appconfig. CLI `metagit merge` + MCP tools.

**Tech Stack:** GitPython, Pydantic, Click, MCP, pytest with temp git repos.

**Design:** [2026-07-09-rfc-0011-merge-orchestrator-design.md](../specs/2026-07-09-rfc-0011-merge-orchestrator-design.md)

## Out of scope

Replacing GitHub/GitLab CI, scheduler, auto ACL allocate for merge agents (hints only), SPA, force-push bypasses.

## File map

| Action | Path |
|--------|------|
| Create | `src/metagit/core/merge/{__init__,models,paths,store,service,validators}.py` |
| Create | `src/metagit/cli/commands/merge_cmd.py` (name avoids stdlib clash if needed) |
| Create | `tests/core/merge/`, CLI tests with temp repos |
| Create | `docs/reference/merge-orchestrator.md` |
| Modify | appconfig for validator hooks; MCP; modality-parity; event feed; CHANGELOG; ROUTER; series index |

## Phases

- [ ] **Phase 0 — Models/store:** merge request record, statuses (`queued|running|succeeded|failed|conflict`).
- [ ] **Phase 1 — Enqueue + integrate:** merge agent branch → integration; persist result; abort cleanly on conflict with structured files list.
- [ ] **Phase 2 — Events + dispatch hints:** `ConflictDetected` / merge events; optional merge-agent `acl_commands` in payload.
- [ ] **Phase 3 — Validators:** opt-in command list; record stdout/stderr/exit; block `promote` on failure.
- [ ] **Phase 4 — Promote (optional):** integration → feature as explicit step.
- [ ] **Phase 5 — CLI/MCP/docs/QA.**

## Acceptance checklist

- [ ] Clean merge succeeds in temp repo test.
- [ ] Conflict produces record without leaving integration in bad recorded state.
- [ ] Validators opt-in default empty.
- [ ] `task qa:prepush` green.

## Expand-at-MR-start

Prioritize Phase 1 git safety tests before CLI polish; impact-analyze any shared git helpers.
