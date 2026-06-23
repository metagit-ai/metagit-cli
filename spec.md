## Tier 1 — biggest leverage

**1. One session-start envelope.** Today bootstrapping is two-plus calls (`context pack --tier 2 --json` + `prompt workspace --kind session-start` + eyeballing approvals/objectives). I'd kill for:
```
metagit session begin --json
```
returning one deterministic blob: workspace map, active project, restored session fields, open objectives, pending approvals, recent handoffs, git dirty state, and any staleness warnings. One round-trip, one token budget, one shape to parse. This is the single highest-value thing.

**2. Token-budgeted packing.** Tiers 0/1/2 are coarse. Let me say `context pack --max-tokens 8000 --json` and have it pack greedily to budget, then tell me *what it dropped and why*. Agents are bounded by the window, not by your tier taxonomy.

**3. `schema_version` on every `--json` payload + a `metagit schema <cmd>` that emits JSON Schema.** When you variablize the session location (or anything) next release, my parsers break silently. A version field lets me branch; published schemas let me self-validate instead of guessing field names from docs.

## Tier 2 — multi-agent coordination

**4. Handoffs as a first-class verb, not file-poking.** `metagit handoff create|claim|list|complete --json` with an append-only audit trail. Right now coordination state is implicit; make the handoff the object.

**5. Approvals as an API I can act on.** `metagit approval list|show|approve|reject --json` with idempotency keys. I can *see* `pending.json` but acting on it should be a contract, not me editing a file behind your back.

**6. Exit codes as a contract.** Distinct nonzero codes for `STALE_INDEX`, `NO_WORKSPACE`, `LOCK_CONTENTION`, `NEEDS_APPROVAL`. Then I branch on `$?` instead of regexing prose out of stderr — which is brittle and burns tokens.

**7. Lease/lock signal.** Your own context-pack skill flags digest-boundary races and concurrent objective upserts. Expose `metagit lock acquire <scope> --ttl` or have writes return `LOCK_CONTENTION` + current holder. This is what makes parallel agents *safe* rather than hopeful.

## Tier 3 — durability & efficiency

**8. Durable objectives.** This is the gap from a minute ago: objectives encode *intent* but live in gitignored `.metagit/`, so they're machine-local and unbacked. `metagit objective export/import --json` (secret-scrubbed) gives me a portable, syncable intent layer without un-ignoring the churny approval/session state.

**9. A `--since` event cursor.** `metagit events --since <cursor> --json` — what objectives/approvals/snapshots changed since I last looked. A long-running orchestrator shouldn't re-pull the whole world every tick.

**10. Universal `--dry-run` returning the plan as JSON.** Matches your own stated preference (preview before destructive). Any state mutation should be able to tell me what it *would* change before it does.

---

If I had to pick three to ship first: **#1 (session begin)**, **#3 (schema_version + exit codes — bundle with #6)**, and **#4/#5 (handoffs + approvals as verbs)**. Those convert metagit from "CLI I scrape" into "API I orchestrate against."

Want me to write these up as objectives/issues *in* metagit itself — dogfooding the objective layer — or drop them as GitHub issues on metagit-ai/metagit-cli? I can draft either with acceptance criteria.

---

## Metagit Implementation Plan (2026-06)

### What Was Added Now

1. Added `config.workspace.session_path` to `metagit.config.yaml` modeling and schema.
2. Added `METAGIT_WORKSPACE_SESSION_PATH` environment override support.
3. Made session persistence honor configurable session path in `SessionStore`.

### Proposed Roadmap For The Remaining Spec

#### Phase 1: Session Contract Foundation (highest leverage)

1. Add `metagit session begin --json` (MCP + CLI parity).
2. Introduce `schema_version` on every JSON response envelope.
3. Define stable non-zero exit code map for machine-branching:
	1. `NO_WORKSPACE`
	2. `STALE_INDEX`
	3. `LOCK_CONTENTION`
	4. `NEEDS_APPROVAL`

Acceptance criteria:
1. One command returns a deterministic session bootstrap payload with explicit field-level schema.
2. Existing commands maintain backward compatibility when `schema_version` is omitted by older clients.
3. Exit codes are documented and integration-tested in shell-level tests.

#### Phase 2: Coordination Primitives

1. Add first-class handoff APIs/commands:
	1. `handoff create`
	2. `handoff claim`
	3. `handoff list`
	4. `handoff complete`
2. Add approvals mutation verbs with idempotency key support.
3. Add lightweight lease API (`lock acquire/release/heartbeat`) for write-critical operations.

Acceptance criteria:
1. Concurrent-agent write operations fail safely with deterministic lock/lease feedback.
2. Approvals and handoffs are no longer dependent on direct file mutation.

#### Phase 3: Efficiency and Durability

1. Add `context pack --max-tokens` greedy packer with explainable drops.
2. Add objective export/import format with redaction-safe defaults.
3. Add event cursor stream: `events --since <cursor>`.
4. Standardize `--dry-run` JSON plan output on all state mutators.

Acceptance criteria:
1. Long-running orchestrators can poll incrementally without full-state reloads.
2. Objective history can be moved across machines without leaking sensitive content.

### Notes On Scope

1. The newly-added `workspace.session_path` unblocks upcoming schema-versioned state migrations.
2. `approval` and `snapshot` storage remain in current locations for now; consider introducing `workspace.state_root` in a later phase to centralize all mutable state paths.