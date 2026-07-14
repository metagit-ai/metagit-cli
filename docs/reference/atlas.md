---
title: Metagit Atlas
---

<!-- modality:atlas_local -->

# Metagit Atlas (RFC-0014)

Atlas is a repository-local semantic layer stored in `.atlas/`. It combines
human-curated intent (capabilities, concepts, invariants, and decisions) with
deterministically generated implementation evidence (inventory, Python symbols,
and test discovery). Source code remains authoritative for implementation;
Atlas records reviewed semantic metadata and reproducible observations.

## Layout

```text
.atlas/
├── atlas.yaml          # repository identity and generation freshness
├── README.md
├── ontology/           # curated concepts and capabilities
├── intent/             # curated contracts, invariants, decisions, and risks
├── generated/          # deterministic evidence artifacts
├── mappings/           # curated semantic-to-evidence links
├── overrides/          # explicit curated corrections
├── policy/             # generation and access policy
└── index/              # rebuildable JSON query index (gitignored)
```

Curated directories are never replaced by generation. `.atlas/index/` is a
derived cache and should not be committed.

## CLI

Atlas operates on the repository given by `--path` (the current directory by
default) and does not require a workspace `.metagit.yml`.

```bash
# Create the layout, then optionally generate the first evidence snapshot.
metagit atlas init --path /path/to/repo
metagit atlas init --path /path/to/repo --generate

# Generate deterministic inventory, symbol, and verification evidence.
metagit atlas generate --path /path/to/repo

# Validate configuration, curated entities, and references.
metagit atlas validate --path /path/to/repo

# Inspect initialization, generation, and freshness state.
metagit atlas status --path /path/to/repo

# Query a curated entity or traverse local relationships.
metagit atlas query 'Capability[id="capability:refund.issue"]' --path /path/to/repo

# Refresh evidence after named source files change.
metagit atlas refresh src/toy/refunds.py --path /path/to/repo
```

Use `--json` with each command for machine-readable output.

## Boundaries

- **RFC-0010 semantic knowledge graph:** workspace-level concept-to-path
  ownership and advisory claim guidance under `.metagit/graph/`. Atlas is a
  richer, repository-local map of intent and evidence under `.atlas/`; neither
  replaces the other.
- **GitNexus:** structural and call-graph intelligence. Atlas does not require
  GitNexus in Phase 0–1 and does not import from it.
- **Context packs / RFC-0009 compiler:** bounded workspace and task context.
  Atlas does not replace them; a later compiler integration may include Atlas
  slices when useful.

## Deferred beyond Phase 1

Phase 2+ may add read-only MCP discovery and context tools, while later phases
cover federation across repositories and optional adapters for GitNexus, mex,
and other extractors. These integrations are intentionally absent from the
local Phase 0–1 MVP.
