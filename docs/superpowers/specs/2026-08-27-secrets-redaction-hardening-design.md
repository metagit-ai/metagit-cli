# Secrets & Redaction Hardening — Incremental Design

**Status:** Proposed  
**Date:** 2026-08-27  
**Series:** [Agent Reliability series index](2026-08-27-agent-reliability-series-index.md)  
**Depends on:** Shipped `metagit.core.routing.redaction` (`redact_run`, `redact_evidence`), run ledger CLI/MCP (`--no-redact`), `metagit.core.web.config_preview.redact_secrets`, context pack service, MCP resources  
**Plan:** (pending — incremental PR, no RFC number)  
**Related:** [Run evidence completion](2026-08-27-rfc-0017-run-evidence-completion-design.md) · RFC-0022 policy audit surfaces

## Summary

Run ledger export already redacts secret-like strings via regex patterns in `redaction.py`. **This incremental design centralizes redaction** into a shared module, extends it to **context packs**, **MCP resource payloads**, and **coordination event feeds**, and aligns prepush **gitleaks** coverage. No new RFC number — ship as a focused PR series before or alongside RFC-0022 policy work.

## Goals

1. **Shared `SecretRedactor` API** — move pattern list + recursive scrub from routing-only module to `metagit.core.security.redaction` (re-export from routing for compatibility).
2. **Context pack redaction** — scrub `agent_instructions_excerpt`, repo card bodies, and tier-2 fragments before JSON export; default **on** for MCP/CLI `--json`.
3. **MCP resources** — apply redaction to resources that may embed env snippets or config previews (`metagit://workspace/*`, config preview paths).
4. **Run ledger parity** — extend patterns (AWS keys, Slack tokens, PEM blocks); keep `evidence.redacted` flag semantics.
5. **Event feeds** — optional redaction pass on `.metagit/events/*.jsonl` export helpers (not on live append — performance).
6. **Document safe token handling** — `docs/reference/secrets-handling.md` + agents.md subsection (env vars, `--no-redact` operator escape hatch).
7. **Prepush alignment** — ensure gitleaks runs when secrets-related paths change; document optional local hook.

## Non-Goals

- Secret scanning of managed repo source trees (use gitleaks/bespoke CI in each repo).
- Encryption at rest for run ledger or plane documents.
- Automatic secret rotation or vault integration (SecretZero remains external skill).
- Blocking commits that contain secrets in metagit workspace state (report-only in metagit; git hooks separate).
- ML-based secret detection.

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | **Regex-first** v1 — no new dependencies; extend `_SECRET_PATTERNS` conservatively. |
| D2 | **Default redact on agent-facing exports** — CLI/MCP JSON defaults `redact=true`; human text mode may show warnings only. |
| D3 | **`--no-redact` remains** for operator debugging — requires explicit flag; logged when used. |
| D4 | Central module **re-exports** routing helpers — no breaking import paths in one release. |
| D5 | Redaction is **lossy scrub** (`[REDACTED]`) — not format-preserving tokenization. |
| D6 | PEM / multiline secrets: dedicated pattern block for `BEGIN … PRIVATE KEY`. |
| D7 | Config preview web path uses **same redactor** — delete duplicate `redact_secrets` implementation after migration. |

## Architecture

```text
Export surfaces (run show, context pack, MCP resource, event export)
              │
              ▼
        SecretRedactor
          ├─► scrub_text(str)
          ├─► scrub_obj(Any)   # recursive dict/list/str
          └─► patterns[]       # compiled regex tuple
              │
              ▼
        Optional RedactionReport { fields_scrubbed, patterns_matched[] }
```

**Module layout (proposed):**

| Module | Role |
|--------|------|
| `src/metagit/core/security/redaction.py` | Canonical patterns + `SecretRedactor` |
| `src/metagit/core/routing/redaction.py` | Thin wrapper → `redact_run` / `redact_evidence` |
| `src/metagit/core/context/redaction_hook.py` | Context pack post-processor |
| `src/metagit/core/mcp/redaction.py` | MCP tool/resource wrapper |

## Pattern catalog (v1 extensions)

Existing patterns (from routing):

- `(api_key|token|secret|password|authorization) = …`
- `Bearer …`
- GitHub `ghp_`, GitLab `glpat-`, OpenAI `sk-`

Add:

| Pattern | Example |
|---------|---------|
| AWS access key | `AKIA[0-9A-Z]{16}` |
| AWS secret (heuristic) | 40-char base64 adjacent to `aws_secret` key |
| Slack token | `xox[baprs]-…` |
| PEM block | `-----BEGIN … PRIVATE KEY-----` … `-----END` |
| JDBC URL password | `jdbc:…:password=…` |
| `.env` assignment | `^[A-Z_]+=.{8,}$` in known secret key names only (narrow) |

Patterns MUST avoid aggressive scrubbing of short hex strings (git shas) — use word boundaries and key names.

## Integration points

| Surface | When | Default |
|---------|------|---------|
| `metagit run show/replay/export` | existing | redact=true |
| `metagit context pack --json` | before serialize | redact=true |
| `metagit context repomix` | out of scope v1 (already profile-controlled) |
| MCP `metagit_context_pack` | `redact` arg default true | |
| MCP run tools | existing | |
| Web config preview | always | redact |
| `metagit context events --export` | new optional path | redact=true |

Context pack adds field `redaction_applied: bool` on result when any field scrubbed.

## Interfaces

No new top-level CLI group. Optional:

```bash
metagit security redaction test --stdin   # read stdin, write scrubbed stdout (operator/debug)
```

MCP: no new tools required; extend existing tool schemas with documented `redact` default.

### Model addition

```python
class RedactionReport(BaseModel):
    redaction_applied: bool = False
    fields_scrubbed: list[str] = Field(default_factory=list)
    patterns_matched: list[str] = Field(default_factory=list)  # pattern category ids, not secrets
```

## Persistence

None. Redaction is transform-on-read/export only — source records unchanged unless operator re-saves with `--no-redact` (discouraged).

## Testing

- Unit tests: each pattern category, nested dict scrub, false-positive guards (git sha, short tokens).
- Extend `tests/core/routing/test_run_ledger.py` imports to canonical module.
- Context pack fixture with fake `api_key=…` in instructions excerpt → scrubbed in JSON output.
- Snapshot test: `--no-redact` preserves raw (operator path).

## Acceptance

- `SecretRedactor` used by routing, context pack, web config preview (duplicate removed).
- `metagit context pack --tier 1 --json` scrubs secrets in card excerpts by default.
- MCP context pack default `redact=true` documented in modality registry.
- Extended patterns covered by unit tests without regressing run ledger tests.
- `docs/reference/secrets-handling.md` documents `--no-redact`, env-var guidance, gitleaks in prepush.
- Series index row updated to link this design; no RFC number assigned.

## Suggested PR split

1. **Central module + routing migration** — move patterns, re-export, tests.
2. **Context pack + MCP** — hook + `redaction_applied` field.
3. **Web config preview dedupe** — single redactor.
4. **Docs + prepush note** — secrets-handling.md, agents.md blurb.

## Open questions

1. Scrub manifest `url` fields with embedded tokens?  
   **Recommendation:** yes when `://` + `@` or `token=` detected in URL userinfo/query.
2. Redact coordination event payloads on **live** `context events` read?  
   **Recommendation:** yes for MCP/CLI JSON; human text may omit detail fields.
