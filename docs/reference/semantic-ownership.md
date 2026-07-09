# Semantic Ownership

<!-- modality:semantic_ownership -->

Semantic ownership records concept-level responsibility across repository path
patterns. It gives agents and operators a lightweight way to ask "who owns this
area of meaning?" before they claim files, split work, or review overlapping
changes.

The RFC-0010 implementation is advisory. It helps explain and route work, but it
does not block Git operations, enforce hard locks, or replace GitNexus.

## Persistence

Semantic graph state lives under the session/manifest root:

```text
.metagit/
  graph/
    concepts.json
    ownerships.json
    ingest-hints.json   # optional operator-supplied input
  events/
    semantic.jsonl
```

`concepts.json` stores canonical concept rows such as `authentication` or
`billing`. `ownerships.json` stores repository-scoped path patterns for each
concept. Semantic lifecycle events append to `.metagit/events/semantic.jsonl`
and appear in `metagit context events` with `source: semantic`.

Event kinds include:

| Event | When emitted |
|-------|--------------|
| `ConceptDeclared` | A manual or service declaration creates concept ownership |
| `ConceptConflictHint` | Multiple active ACL claim agents overlap one concept |
| `ConceptIngested` | Deterministic ingest adds ownership hints |

## CLI and MCP

CLI commands use the same session-root resolution as ACL commands. Pass
`--definition path/to/.metagit.yml` when running outside the manifest root.

| Goal | CLI | MCP tool |
|------|-----|----------|
| Declare concept ownership | `metagit semantic declare --concept C --repository project/repo --pattern 'src/**' --json` | `metagit_semantic_declare` |
| Query a concept | `metagit semantic query --concept C --json` | `metagit_semantic_query` |
| Resolve path owners | `metagit semantic owners --repository project/repo --path src/file.py --json` | `metagit_semantic_owners` |
| Show claim overlap hints | `metagit semantic conflicts --repository project/repo --json` | `metagit_semantic_conflicts` |
| Ingest deterministic hints | `metagit semantic ingest --json` | `metagit_semantic_ingest` |
| Seed the static catalog | `metagit semantic seed --repository project/repo --json` | Not exposed in MCP v1 |

MCP semantic tools are available only when the workspace gate is ACTIVE.

## Advisory Claim Hints

ACL file claims remain advisory and Git remains authoritative. Semantic
ownership adds a second, softer signal: when `metagit claim check` or MCP claim
checks evaluate a path pattern, the result may include `concept_hints` for
overlapping semantic ownership patterns.

These hints do not make the claim fail. They are intended for coordination:

- route a task to a likely concept owner;
- warn an agent that a claimed file belongs to a broader product concept;
- explain why two active claims may be related even when their file patterns do
  not directly collide.

Use `metagit semantic conflicts --repository project/repo --json` to find active
ACL claims from multiple agents that overlap the same concept ownership.

## Seed and Ingest

Semantic ownership is empty by default. Operators opt in to concept data.

`metagit semantic seed --repository project/repo --json` inserts a small static
catalog of common concepts, with repository ownership patterns marked
`source: seed`. Re-running the command is idempotent.

`metagit semantic ingest --json` reads deterministic hints from
`.metagit/graph/ingest-hints.json` when present. A minimal hints file looks like:

```json
{
  "ownerships": [
    {
      "concept": "Authentication",
      "repository": "platform/api",
      "patterns": ["backend/auth/**", "backend/login/**"]
    }
  ]
}
```

If the hints file is absent or empty, ingest returns success with
`reason: "no_ingest_signals"`. It does not call LLMs or infer ownership from
repository contents.

## Deferred GitNexus Import

Task 9 (`semantic ingest --gitnexus`) is deferred. RFC-0010 intentionally ships
without a GitNexus import path; future work may add a read-only adapter that
imports concept/path hints from GitNexus group or query results. Until then,
operators should use manual declarations, the seed catalog, or
`ingest-hints.json`.

## Non-goals

- Semantic ownership is not a GitNexus replacement.
- Semantic ownership is not a source-code knowledge graph, vector index, or
  whole-repo semantic search engine.
- Semantic ownership does not enforce hard locks or block Git.
- Semantic ownership does not replace ACL branch leases, worktrees, or file
  claims.
- RFC-0010 does not implement RFC-0011 merge orchestration, RFC-0012 scheduling,
  or RFC-0013 AOS composition.
