---
title: Merge Orchestrator
---

<!-- modality:merge_orchestrator -->

# Merge Orchestrator

RFC-0011 adds a local merge queue for agent branches, integration branches,
opt-in validators, conflict records, and CLI/MCP parity.

The orchestrator is deliberately local. It records intent and attempts merges in
an existing checkout; it does not push, force-push, allocate ACL resources, or
replace CI.

## Model

Merge requests live under the manifest/session root:

```text
.metagit/
  merges/
    queue.json
    <merge_id>.json
  events/
    merge.jsonl
```

Statuses:

| Status | Meaning |
|--------|---------|
| `queued` | Request is recorded and ready to integrate. |
| `running` | Local merge attempt is in progress. |
| `succeeded` | Source branch merged into the integration branch and validators passed. |
| `failed` | Git operation or service step failed without conflict details. |
| `conflict` | Git reported conflicts; the merge was aborted cleanly. |
| `validation_failed` | Integration merge completed, but an opt-in validator failed. |

Conflict records include conflicting paths, a dispatch hint, and advisory
`acl_commands`. These commands are suggestions only. The orchestrator does not
run `metagit branch`, `lease`, `worktree`, or `claim` automatically.

## CLI

```bash
# Enqueue an agent branch for local integration
metagit merge enqueue \
  --repository project/repo \
  --branch agent/task-123 \
  --into integration/task-123 \
  --repo-path /path/to/repo \
  --json

# Attempt the merge into the integration branch
metagit merge integrate --merge-id <merge-id> --json

# Inspect merge records
metagit merge status --repository project/repo --json

# Retry after fixing a failed/conflicting/validation-failed request
metagit merge retry --merge-id <merge-id> --json

# Explicitly promote the validated integration branch into another branch
metagit merge promote --merge-id <merge-id> --into main --json
```

Use `--definition path/to/.metagit.yml` when running outside the manifest root.
`--repo-path` is accepted on enqueue and on later commands for test or recovery
flows where a stored request needs its checkout path updated.

## Validators

Validators are opt-in and default to an empty list:

```yaml
merge:
  validators:
    - uv run pytest tests/core/merge
    - uv run ruff check src/metagit/core/merge tests/core/merge
```

Commands run in the target repository checkout via the platform shell
(`shell=True`: `/bin/sh` on Unix, `ComSpec`/`cmd.exe` on Windows). stdout, stderr,
and exit codes are stored on the merge request. The first non-zero exit code
marks the request `validation_failed` and blocks `promote`.

Empty validators still record a successful validation result so downstream
adapters can distinguish "validated successfully" from "not integrated yet".

## MCP Tools

When the workspace gate is ACTIVE:

| Tool | Required arguments | Purpose |
|------|--------------------|---------|
| `metagit_merge_enqueue` | `repository`, `source_branch`, `target_branch` | Record a queued merge request. |
| `metagit_merge_status` | none | List merge requests, optionally filtered by `repository`. |
| `metagit_merge_integrate` | `merge_id` | Attempt the source-to-integration merge. |
| `metagit_merge_retry` | `merge_id` | Requeue and integrate a failed/conflicting/validation-failed request. |

The MCP surface returns the same JSON shapes as the core service
(`model_dump(mode="json")`) and uses the same persistence under `.metagit/`.

## Events

Merge lifecycle events append to `.metagit/events/merge.jsonl` and appear in
`metagit context events` with `source: merge`.

Event kinds:

- `MergeEnqueued`
- `MergeSucceeded`
- `MergeFailed`
- `ConflictDetected`
- `MergeValidationFailed`
- `MergePromoted`

## Safety Boundaries

- No push or force-push is performed.
- On conflict, GitPython merge helpers abort cleanly before returning.
- ACL command strings are advisory dispatch hints only.
- Validators are configured explicitly; the default list is empty.
- Promotion is explicit and gated by `succeeded` status plus successful
  validation.
