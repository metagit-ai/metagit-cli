# Reference rewrite workspace

Use this guide when an orchestrator agent coordinates a **reference-implementation rewrite**:
one repository holds the canonical behavior (source) and a sibling repository holds the
new implementation (target) — for example migrating **metagit-cli** from Python to Rust.

Metagit does not ship a first-class module-parity schema. Instead it combines:

- **Workspace catalog** — source + target repos under one project
- **Campaign overlay** — frozen repo set, `reference_impl`, MR rollups
- **Parity registry convention** — `_rewrite/parity-registry.yml` for phase/module mapping
- **Objectives + handoffs** — active work items and subagent delegation
- **`graph.relationships`** — durable source ↔ target edge for GitNexus and web graph

## Quick start

### Option A — init template

```bash
metagit init ./rewrite-coordinator --create --template metagit-rewrite
cd rewrite-coordinator

# Or non-interactive:
metagit init --target ./rewrite-coordinator --create --template metagit-rewrite \
  --answers-file examples/metagit-rewrite/answers.example.yml --no-prompt
```

### Option B — copy the example manifest

Copy [examples/metagit-rewrite/.metagit.yml](../examples/metagit-rewrite/.metagit.yml)
into your coordinator repository and adjust repo URLs.

### Wire app config and sync

```yaml
# metagit.config.yaml
config:
  workspace:
    path: ./.metagit
    campaigns_path: _campaigns
```

```bash
metagit config validate
metagit project sync --project rewrite
metagit campaign validate
```

## Layout

```
rewrite-coordinator/          # umbrella repo (this manifest lives here)
├── .metagit.yml
├── AGENTS.md
├── _campaigns/
│   └── language-rewrite.yml  # repo-level rollup (committed)
├── _rewrite/
│   └── parity-registry.yml   # module-level parity (BYO convention)
└── .metagit/                 # sessions, objectives, approvals (gitignored sync tree)
```

Cloned repos appear under your configured `workspace.path` (default `./.metagit`):

```
.metagit/rewrite/source/      # reference implementation
.metagit/rewrite/target/      # rewrite implementation
```

## Granularity

| Concern | Mechanism | Example |
|---------|-----------|---------|
| Repo pair | `.metagit.yml` | `rewrite/source`, `rewrite/target` |
| Reference spec | `reference_impl` on campaign | `rewrite/source` |
| Repo status / MR | `_campaigns/<slug>.yml` | `status: mr-open`, `mr:` URL |
| Module parity | `_rewrite/parity-registry.yml` | `config-manager` phase module |
| Active task | objectives JSON | `rewrite-foundation-config-manager` |
| Cross-repo semantics | `graph.relationships` | `target` **implements** `source` |

See [objectives.example.json](../examples/metagit-rewrite/objectives.example.json)
for sample objective payloads.

## Orchestrator workflow

1. **Session bootstrap** — tier-2 context pack + `session-start` prompt
2. **Campaign rollup** — `metagit campaign status --slug language-rewrite --json`
3. **Pick next module** — first `pending` entry in parity registry
4. **Objective upsert** — `metagit context objective set` with acceptance criteria
5. **Subagent dispatch** — repo-scoped handoff to target (or source for analysis)
6. **Record MR** — `metagit campaign set` + objective `mr_url`
7. **Poll** — `metagit context events --campaign language-rewrite`

Full playbook: bundled skill **`metagit-rewrite-campaign`**.

```bash
metagit skills install --skill metagit-rewrite-campaign --target cursor
```

Helper script (when skill tree is installed):

```bash
./scripts/rewrite-orchestrator-cycle.sh . language-rewrite
```

## Campaign commands

```bash
metagit campaign new --slug language-rewrite --title "Language rewrite" \
  --repo rewrite/source --repo rewrite/target \
  --reference rewrite/source \
  --goal "CLI and MCP parity with Python reference"

metagit campaign expand --slug language-rewrite --dry-run
metagit campaign expand --slug language-rewrite

metagit campaign set --slug language-rewrite --repo rewrite/target \
  --status mr-open --mr "https://github.com/org/repo/pull/42"

metagit campaign status --slug language-rewrite --json
```

## Repomix profiles

Bundled context profiles scope analysis and implementation:

```bash
metagit context repomix --profile rewrite-source --project rewrite --repo source
metagit context repomix --profile rewrite-target --project rewrite --repo target
```

## Agent profiles

The example manifest declares different posture per repo:

- **Source** — read-only analysis skills (`metagit-gitnexus`, `metagit-repo-impact`)
- **Target** — full implementation skills (`metagit-rewrite-campaign`, `metagit-release-audit`)

Materialize before dispatch:

```bash
metagit agent apply --vendor claude_code --project rewrite --repo target
```

See [Agent profile](reference/agent-profile.md).

## Multi-agent shared state

When subagents run on separate machines, point them at a shared ops backend:

```bash
metagit web serve
export METAGIT_STATE_URL=http://127.0.0.1:8765
```

See [Sharing state across a team](reference/sharing-state.md).

## Metagit self-rewrite example

To migrate **metagit-cli** itself:

1. Create coordinator repo with source = `metagit-ai/metagit-cli`
2. Add target = your new-language fork (empty or scaffold)
3. Seed `_rewrite/parity-registry.yml` from `src/metagit/core/*` component boundaries
4. Use modality registry (`docs/reference/modality-feature-registry.md`) as CLI/MCP parity checklist
5. Fan out objectives per component; track MRs on the target repo only

The source repo stays the behavioral reference until parity gates pass.

## Validation

```bash
metagit config validate -c .metagit.yml
metagit campaign validate
```

Commit `_campaigns/` and `_rewrite/` so reviewers see rollups and parity maps in diffs.

## Related docs

- [Campaigns reference](reference/campaigns.md)
- [Hermes orchestrator workspace](hermes-orchestrator-workspace.md) — general multi-repo control plane
- [Skills — metagit-rewrite-campaign](skills.md)
