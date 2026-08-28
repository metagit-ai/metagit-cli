# RFC-0022: Policy Engine for Mutating Classes — Design

**Status:** Proposed  
**Date:** 2026-08-27  
**Series:** [Agent Reliability series index](2026-08-27-agent-reliability-series-index.md)  
**Depends on:** Shipped routing engine + run ledger (`metagit.core.routing`), RFC-0007 (ACL), RFC-0011 (merge), RFC-0015 (DocumentStore writes), RFC-0016 (catalog mutations, optional), RFC-0017 run evidence  
**Plan:** (pending — `docs/superpowers/plans/2026-08-27-rfc-0022-policy-engine.md`)  
**Related:** [Routing engine spec](2026-08-10-metagit-routing-engine-spec.md) · [Run evidence completion](2026-08-27-rfc-0017-run-evidence-completion-design.md)

## Summary

Agents operating under `METAGIT_AGENT_MODE=true` need a **declarative, auditable gate** before high-impact mutations — ACL bind, merge integrate, catalog push, remote state writes — without replacing existing routing tier promotion or scheduler policy. **RFC-0022 adds a thin `PolicyEngine`** that evaluates workspace-defined rules against a normalized **action envelope**, returns allow/deny with reasons, and **records decisions into the run ledger** when a run is active. v1 ships **report-only by default**; default-deny for configured high-risk classes applies only when explicitly enabled and after happy-path scenario tests remain green.

## Goals

1. **Declarative policy document** — YAML under `.metagit/policy/` (or extend `routing.policy`) describing rules keyed by **action class** (`acl.bind`, `merge.integrate`, `catalog.push`, `state.put`, …).
2. **`PolicyEngine.eval(action, context) → PolicyDecision`** — pure evaluation over pydantic models; no side effects except optional audit append.
3. **CLI `metagit policy eval|show|validate`** — JSON-first; `eval --action … --json` for agent preflight; `show` dumps effective rules; `validate` checks schema + unknown action refs.
4. **Hook points** — call sites before mutating operations in ACL bind, merge integrate, catalog push/save, DocumentStore `put` (when `config.state` enabled). v1: **warn + block only when `policy.enforcement=strict`**.
5. **Run ledger audit** — when routing run is open, append `policy_eval` step to `RunEvidence.steps[]` with `{action, decision, rule_id, reason}`.
6. **Agent-mode posture** — optional `policy.agent_mode.default_deny_classes[]` for high-risk actions; **not enabled globally** until RFC-0021 scenarios + existing integration tests pass with enforcement on (series D4).
7. **Parity** — MCP `metagit_policy_eval`, skill `metagit-gating`, docs `docs/reference/policy-engine.md`, modality registry.

## Non-Goals

- Replacing routing **tier promotion** (`lane eval`, mutating-class ceiling) — policy complements, does not duplicate, the routing safety invariant.
- Replacing scheduler `SchedulePolicy` weights — orthogonal concern.
- A general-purpose OPA/Rego or IAM product — keep rules in metagit YAML with a small built-in evaluator.
- Automatic policy generation from run history (defer).
- Blocking read-only surfaces (context pack, grep, doctor, policy eval itself).
- Federation cross-workspace policy (RFC-0023) — rules are workspace-local in v1.

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | Policy lives in **workspace config files**, not plane-only — plane overlay is optional follow-on with RFC-0016. |
| D2 | **Default enforcement mode is `report`** — evaluate, log/audit, never block unless `policy.enforcement: strict`. |
| D3 | **`strict` enforcement** requires explicit config; flipping agent-mode default-deny is a **separate opt-in flag** (`policy.agent_mode.enforce_deny: true`). |
| D4 | Deny decisions return structured `PolicyDecision` with `code`, `rule_id`, `message`, `remediation[]` — never bare exceptions in agent mode. |
| D5 | Rules match on **`action` + optional dimensions** (`project`, `repo`, `agent_id`, `route_class`, `mutates`, `tier`) — no arbitrary Python expressions in v1. |
| D6 | **Audit always** when routing configured and run open; audit to stderr/log when no run (same pattern as routing hooks). |
| D7 | Policy eval is **idempotent and side-effect free** — safe to call from doctor, aos next preview, and MCP preflight. |
| D8 | Unknown actions in rules → `validate` warning; at eval time unknown action keys fall through to **implicit allow** in `report` mode, **implicit deny** in `strict` when `policy.default: deny`. |

## Architecture

```text
Mutating command (acl bind, merge integrate, catalog push, state put)
              │
              ▼
        PolicyGate.check(action_envelope)
              │
              ▼
        PolicyEngine.eval()
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
 PolicyStore  RuleMatcher  AuditWriter
 (.metagit/   (conditions)  → RunEvidence step
  policy/)                    or PolicyEvent JSONL
              │
              ▼
     allow → proceed | deny → PolicyDeniedError (strict)
                         or warn + proceed (report)
```

**Package placement (proposed):**

| Module | Role |
|--------|------|
| `src/metagit/core/policy/models.py` | `PolicyDocument`, `PolicyRule`, `PolicyAction`, `PolicyDecision`, `PolicyContext` |
| `src/metagit/core/policy/engine.py` | `PolicyEngine`, `RuleMatcher` |
| `src/metagit/core/policy/store.py` | Load/merge policy files from `.metagit/policy/` + optional manifest inline block |
| `src/metagit/core/policy/gate.py` | `PolicyGate` — thin wrapper for call sites |
| `src/metagit/core/policy/audit.py` | Append to run ledger + optional `.metagit/events/policy.jsonl` |
| `src/metagit/cli/commands/policy.py` | `eval`, `show`, `validate` |

**Relationship to routing promotion policy:**

| Surface | Role |
|---------|------|
| `routing.policy.promote_after_clean` | Tier promotion thresholds — **unchanged** |
| `policy.rules[]` | Pre-mutation allow/deny — **new** |
| `RequestClass.mutates` | Feeds `context.mutates` for eval; routing ceiling invariant unchanged |

## Policy document shape (v1)

Default path: `.metagit/policy/rules.yaml`. Optional manifest reference:

```yaml
policy:
  enforcement: report          # report | strict
  default: allow               # allow | deny (applies in strict when no rule matches)
  agent_mode:
    enforce_deny: false        # when true + METAGIT_AGENT_MODE, apply default_deny_classes
    default_deny_classes:
      - state.put
      - catalog.push
  rules:
    - id: deny-merge-without-lease
      action: merge.integrate
      effect: deny
      when:
        acl_active_lease: false
      message: "Merge integrate requires active ACL lease on target repo"
      remediation:
        - "metagit lease acquire --allocate …"
    - id: allow-aos-bind-skilled
      action: acl.bind
      effect: allow
      when:
        route_tier_in: [skilled, novel]
      message: "ACL bind permitted for non-deterministic tiers"
    - id: audit-catalog-push
      action: catalog.push
      effect: allow
      audit: true
```

**Supported `action` values (v1):**

| Action | Hook site |
|--------|-----------|
| `acl.bind` | Branch allocate + lease + worktree bind path |
| `acl.claim.declare` | Claim declare with `allow_conflicts=False` |
| `merge.integrate` | Merge orchestrator integrate |
| `merge.enqueue` | Merge enqueue |
| `catalog.push` | Catalog plane/manifest push |
| `catalog.mutate` | Workspace add/remove repo |
| `state.put` | DocumentStore CAS write |
| `task.complete` | Task node completion (optional v1.1) |
| `aos.recover` | RFC-0019 recover with destructive flags |

**Condition keys (`when`):**

| Key | Type | Meaning |
|-----|------|---------|
| `project` | string | Exact project name |
| `repo` | string | Exact repo name |
| `agent_id` | string | Calling agent |
| `route_class` | string | Routing class id when present |
| `route_tier_in` | list[Tier] | Routing tier membership |
| `mutates` | bool | From route class or action default |
| `acl_active_lease` | bool | Agent holds active lease on repo |
| `agent_mode` | bool | `METAGIT_AGENT_MODE` set |
| `env` | map | Exact env var presence/value match |

Rules are evaluated **first match wins** by file order; later rules may override if `priority` field added in v1.1 — v1 uses declaration order only.

## Interfaces

### CLI

```bash
metagit policy show [--json]
metagit policy validate [--json]
metagit policy eval --action acl.bind \
  [--project P] [--repo R] [--agent-id A] \
  [--route-class REQ-…] [--json]
```

**`policy eval` output (JSON):**

```json
{
  "action": "acl.bind",
  "decision": "allow",
  "enforcement": "report",
  "rule_id": "allow-aos-bind-skilled",
  "message": "ACL bind permitted for non-deterministic tiers",
  "remediation": [],
  "would_block_in_strict": false,
  "audited": true
}
```

### MCP (ACTIVE-gated)

| Tool | Purpose |
|------|---------|
| `metagit_policy_show` | Effective policy document summary |
| `metagit_policy_validate` | Schema + action ref validation |
| `metagit_policy_eval` | Same as CLI eval |

### Models (proposed)

```python
class PolicyAction(str, Enum):
    ACL_BIND = "acl.bind"
    MERGE_INTEGRATE = "merge.integrate"
    # …

class PolicyContext(BaseModel):
    action: PolicyAction
    agent_id: str | None = None
    project: str | None = None
    repo: str | None = None
    route_class: str | None = None
    route_tier: Tier | None = None
    mutates: bool | None = None
    acl_active_lease: bool | None = None
    agent_mode: bool = False
    run_id: str | None = None

class PolicyDecision(BaseModel):
    action: PolicyAction
    effect: Literal["allow", "deny"]
    enforcement: Literal["report", "strict"]
    rule_id: str | None = None
    message: str
    remediation: list[str] = Field(default_factory=list)
    would_block_in_strict: bool = False
    audited: bool = False
```

### Hook integration pattern

```python
decision = policy_gate.check(PolicyContext(action=PolicyAction.ACL_BIND, ...))
if decision.effect == "deny" and enforcement == "strict":
    return PolicyDeniedError(decision)
# report mode: log warning, continue
```

Call sites inject `policy_gate` optionally — when policy directory absent, gate is no-op allow.

## Persistence

| Artifact | Path | Notes |
|----------|------|-------|
| Policy rules | `.metagit/policy/rules.yaml` | Git-trackable; teams may commit |
| Policy events | `.metagit/events/policy.jsonl` | Append-only audit overlay |
| Run evidence step | per-run YAML under `routing.runs` | `name=policy_eval` step |

No new database. Plane-backed policy document deferred to RFC-0016 mirror mode.

## Run ledger audit

When `run_id` present on context (from active routing run or AOS next):

```python
ControlLoopStep(
    name="policy_eval",
    at=iso_now(),
    status="allow" | "deny",
    detail={
        "action": "acl.bind",
        "rule_id": "…",
        "enforcement": "report",
        "message": "…",
    },
)
```

Uses existing `RoutingService.append_step` — no parallel audit store required.

## Acceptance

- `metagit policy eval --action acl.bind --json` returns deterministic decision for fixture policy files.
- `metagit policy validate` fails on unknown condition keys or malformed YAML.
- With `enforcement: report`, denied rule match logs warning but **does not block** ACL bind in integration test.
- With `enforcement: strict` + deny rule, ACL bind returns non-zero / structured error in agent mode.
- Active run receives `policy_eval` step on gated mutation attempt.
- Agent-mode default-deny classes **disabled by default**; enabling requires `policy.agent_mode.enforce_deny: true` and passes RFC-0021 scenario suite.
- MCP tools mirror CLI JSON shapes.
- Modality entry `policy_engine`; skill `metagit-gating` updated; `docs/reference/policy-engine.md` when shipped.
- `scripts/modality-parity.yml` updated; no public `docs/reference/rfc-0022*` stub until shipped.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| Routing run ledger (shipped) | Audit trail for policy decisions |
| RFC-0007 ACL, RFC-0011 merge | Hook sites |
| RFC-0015/0016 (optional) | `state.put`, `catalog.push` hooks |
| RFC-0021 scenarios | Enforcement regression safety net |
| RFC-0019 recover | Destructive recover flag policy |

## Suggested PR split

1. **Core engine** — models, store, matcher, unit tests (no hooks).
2. **CLI/MCP eval surface** — report-only everywhere.
3. **Hook wiring** — ACL bind + merge integrate behind feature flag / enforcement mode.
4. **Run ledger audit + docs** — steps, skill, reference doc, modality parity.
5. **Strict + agent-mode deny** — gated behind config; scenario test matrix.

## Open questions

1. Should policy rules live **inline in `.metagit.yml`** instead of `.metagit/policy/`?  
   **Recommendation:** support both — inline `policy:` block merges with directory files; directory wins on rule id collision.
2. Integrate with Atlas `access.yaml` classification?  
   **Recommendation:** v1.1 `when.classification_in` condition; Atlas not required for v1.
3. Should `aos next --commit` eval policy before scheduler commit?  
   **Recommendation:** yes for preview path always; block on commit only in strict mode.
