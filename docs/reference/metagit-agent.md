# `metagit agent`

Export and install bundled agent definitions for coding vendors.

Supported vendors: **Claude Code**, **Cursor**, **GitHub Copilot**, **Hermes**,
**OpenClaw**, **OpenCode**, **Windsurf**, **Codex**.

## Commands

| Command | Purpose |
|---------|---------|
| `metagit agent list` | Catalog envelope (`--json`) with taxonomy and `source` |
| `metagit agent show <id>` | Show template manifest (`--json`) |
| `metagit agent schema` | Write `schemas/agent_template.schema.json` |
| `metagit agent validate` | Validate bundled (+ overlay) manifests |
| `metagit agent preview <id>` | Render vendor artifact without writing (`--json`) |
| `metagit agent dispatch-plan <id>` | Install, launch, and handoff envelope (`--json`) |
| `metagit agent overlay init <id>` | Scaffold editable overlay from bundled template |
| `metagit agent overlay path <id>` | Print overlay directory for a template |
| `metagit agent export <id>` | Write vendor-neutral files to `--output` |
| `metagit agent create <id>` | Install into a vendor-specific agents or skills path |

Workspace overlays use a **two-tier** layout under the manifest root (`--root`):

| Scope | Path | Git |
|-------|------|-----|
| **Team (default)** | `.metagit-agents/<id>/` | Commit to git — shared workspace config |
| **Personal** | `.metagit/.agent-templates/<id>/` | Gitignored with `.metagit/` sync/session tree |

Resolution order: **bundled → committed → local** (local wins for conflicts).

### Workspace overlays

Create an editable copy of a bundled template:

```bash
# Team overlay (default) — commit .metagit-agents/ to git
metagit agent overlay init repo-implementer --root .

# Personal override only on this machine
metagit agent overlay init repo-implementer --local --mode minimal --open
```

- **`--mode full`** (default) — copies all bundled `.tpl` files and `template.yaml`
- **`--mode minimal`** — writes a manifest stub plus `body.md.tpl` for small overrides
- **`--local`** — write under gitignored `.metagit/.agent-templates/` instead of `.metagit-agents/`
- **`--force`** — replace an existing overlay directory
- Edits deep-merge with the bundle; run `metagit agent validate --root .` after changes

The Metagit Web **Agents** page scaffolds **team overlays** in `.metagit-agents/`
(`POST /v3/agents/templates/{id}/overlay/init`, `scope: committed`).

### Dispatch plan (overseer handoff)

Turn a template plus project/repo scope into an install, launch, and handoff envelope:

```bash
metagit agent dispatch-plan repo-implementer \
  --project my-api --repo backend \
  --vendor cursor --task "implement auth middleware" \
  --root . --json
```

The JSON payload includes:

- **`install`** — whether the vendor artifact exists, its path, and a suggested `metagit agent create` command
- **`launch`** — per-vendor invoke hints (for example `@repo-implementer` for Cursor)
- **`handoff`** — tiered `context pack` CLI, repo `subagent-handoff` prompt, and layered `effective_instructions`
- **`out_of_scope`** — boundaries derived from template archetype and scope

MCP equivalents: `metagit_agent_catalog`, `metagit_agent_dispatch_plan`.
Web: `GET /v3/agents/templates/{id}/dispatch-plan?vendor=&project=&repo=&task=`.

## Archetypes (schema v1)

| ID | Scope | Category |
|----|-------|----------|
| `orchestration-overseer` | workspace | Control plane |
| `iac-coordinator` | workspace | Control plane |
| `repo-implementer` | repo | Execution |
| `graph-curator` | workspace | Graph |
| `catalog-bootstrapper` | workspace | Workspace ops |
| `upstream-triage` | workspace | Workspace ops |
| `repo-enricher` | repo | Catalog |
| `release-auditor` | workspace | Quality |
| `secret-bootstrapper` | workspace | Security |
| `agent-access-optimizer` | repo | Catalog |

## Templates

### `orchestration-overseer`

Control-plane agent for umbrella workspaces:

- Metagit MCP (and CLI fallbacks) for multi-repo awareness
- Subagent dispatch across `workspace.projects[]`
- Graph discover → suggest → ingest → `gitnexus group sync`
- SecretZero skill/MCP when `Secretfile.yml` exists
- GitNexus wiki refresh from manifest `documentation[]` links

## Quick start

**Claude Code**

```bash
metagit agent create orchestration-overseer --vendor claude_code --scope project
metagit agent create orchestration-overseer --install-skills --install-mcp --vendor claude_code
```

Invoke `@orchestration-overseer` in Claude Code after install.

**Cursor**

```bash
metagit agent create orchestration-overseer --vendor cursor --scope project
metagit agent create orchestration-overseer --install-skills --install-mcp --vendor cursor
```

Invoke `@orchestration-overseer` from the workspace root (`.cursor/agents/`).

**GitHub Copilot (VS Code / Visual Studio)**

```bash
metagit agent create orchestration-overseer --vendor github_copilot --scope project
metagit agent create orchestration-overseer --install-skills --install-mcp --vendor github_copilot
```

Installs `orchestration-overseer.agent.md` under `.github/agents/`. Project MCP
writes to `.vscode/mcp.json` using the VS Code `servers` root key.

**OpenCode**

```bash
metagit agent create orchestration-overseer --vendor opencode --scope project
```

Installs a subagent markdown file with `mode: subagent` frontmatter. Mention
`@orchestration-overseer` in OpenCode.

**Hermes / OpenClaw / Windsurf / Codex (skill install)**

These vendors load control-plane instructions as Agent Skills (`SKILL.md`):

```bash
metagit agent create orchestration-overseer --vendor hermes --scope user
metagit agent create orchestration-overseer --vendor openclaw --scope user
metagit agent create orchestration-overseer --vendor windsurf --scope project
metagit agent create orchestration-overseer --vendor codex --scope project
metagit agent create orchestration-overseer --install-skills --install-mcp --vendor hermes
```

Load the `orchestration-overseer` skill (or let the agent discover it) for
control-plane sessions.

## Export (all artifacts)

```bash
metagit agent export orchestration-overseer -o ./agent-bundle --no-prompt
```

Writes `orchestration-overseer.md`, optional `AGENTS.md.fragment`, and `manifest.json`.

## Options

- `--vendor` / `--target` — vendor id
- `--scope` — `project` (default) or `user`
- `--answers-file` — YAML/JSON template variables
- `--no-prompt` — use defaults only
- `--install-skills` — install `recommended_skills` from template manifest
- `--install-mcp` — write metagit MCP config for the vendor
- `--force` — overwrite existing agent file
- `--dry-run` — preview without writing

## Vendor paths

| Vendor | Project install path | User install path | Kind |
|--------|----------------------|-------------------|------|
| `claude_code` | `.claude/agents/*.md` | `~/.claude/agents/` | agent |
| `cursor` | `.cursor/agents/*.md` | `~/.cursor/agents/` | agent |
| `github_copilot` | `.github/agents/*.agent.md` | `~/.github/agents/` | agent |
| `opencode` | `.opencode/agents/*.md` | `~/.config/opencode/agents/` | agent (subagent) |
| `hermes` | `.hermes/skills/<name>/SKILL.md` | `~/.config/hermes/skills/<name>/` | skill |
| `openclaw` | `.openclaw/skills/<name>/SKILL.md` | `~/.openclaw/skills/<name>/` | skill |
| `windsurf` | `.windsurf/skills/<name>/SKILL.md` | `~/.codeium/windsurf/skills/<name>/` | skill |
| `codex` | `.agents/skills/<name>/SKILL.md` | `~/.agents/skills/<name>/` | skill |

### Skills + MCP paths (`metagit skills install` / `mcp install`)

| Vendor | Project skills | User skills | Project MCP | User MCP |
|--------|----------------|-------------|-------------|----------|
| `claude_code` | `.claude/skills/` | `~/.claude/skills/` | `.claude/mcp.json` | `~/.claude/mcp.json` |
| `cursor` | `.cursor/skills/` | `~/.cursor/skills/` | `.cursor/mcp.json` | `~/.cursor/mcp.json` |
| `github_copilot` | `.github/skills/` | `~/.copilot/skills/` | `.vscode/mcp.json` (`servers`) | `~/.copilot/mcp-config.json` |
| `opencode` | `.opencode/skills/` | `~/.config/opencode/skills/` | `.opencode/mcp.json` | `~/.config/opencode/mcp.json` |
| `hermes` | `.hermes/skills/` | `~/.config/hermes/skills/` | `.hermes/mcp.json` | `~/.config/hermes/mcp.json` |
| `openclaw` | `.openclaw/skills/` | `~/.openclaw/skills/` | `.openclaw/mcp.json` | `~/.openclaw/mcp.json` |
| `windsurf` | `.windsurf/skills/` | `~/.codeium/windsurf/skills/` | `.windsurf/mcp_config.json` | `~/.codeium/windsurf/mcp_config.json` |
| `codex` | `.agents/skills/` | `~/.agents/skills/` | `.codex/mcp.json` | `~/.codex/mcp.json` |

Bundled templates live under `src/metagit/data/agent-templates/` in the repository.
