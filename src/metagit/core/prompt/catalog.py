#!/usr/bin/env python
"""
Built-in operational prompts for metagit agents by scope.
"""

from __future__ import annotations

from metagit.core.prompt.models import PromptCatalogEntry, PromptKind, PromptScope

_CATALOG: list[PromptCatalogEntry] = [
    PromptCatalogEntry(
        kind="instructions",
        title="Composed manifest instructions",
        description=("Layered agent_instructions from .metagit.yml (file → workspace → project → repo)."),
        scopes=["workspace", "project", "repo"],
    ),
    PromptCatalogEntry(
        kind="session-start",
        title="Workspace session bootstrap",
        description="MCP gate, health check, and manifest discovery checklist.",
        scopes=["workspace"],
    ),
    PromptCatalogEntry(
        kind="catalog-edit",
        title="Catalog registration workflow",
        description="Search-before-create and validate manifest edits.",
        scopes=["workspace", "project"],
    ),
    PromptCatalogEntry(
        kind="health-preflight",
        title="Health preflight",
        description="Surface missing clones, duplicates, and branch age before work.",
        scopes=["workspace", "project"],
    ),
    PromptCatalogEntry(
        kind="sync-safe",
        title="Safe repository sync",
        description="Fetch-first sync rules and operator approval for mutation.",
        scopes=["workspace", "project", "repo"],
    ),
    PromptCatalogEntry(
        kind="subagent-handoff",
        title="Subagent handoff",
        description="Delegate single-repo work with repo-scoped instructions.",
        scopes=["project", "repo"],
    ),
    PromptCatalogEntry(
        kind="layout-change",
        title="Layout rename or move",
        description="Dry-run layout operations before manifest and disk changes.",
        scopes=["workspace", "project", "repo"],
    ),
    PromptCatalogEntry(
        kind="repo-enrich",
        title="Repo catalog enrichment",
        description=(
            "Discover repo metadata on disk and merge into the workspace "
            "manifest entry (detect, source sync, validate)."
        ),
        scopes=["repo"],
    ),
    PromptCatalogEntry(
        kind="context-pack",
        title="Tiered context pack",
        description=(
            "Session-start tier-0 pack via CLI or MCP; escalate to tier 1 for "
            "repos in active scope with token-aware budgeting."
        ),
        scopes=["workspace", "project", "repo"],
    ),
    PromptCatalogEntry(
        kind="graph-discover",
        title="Workspace graph discovery",
        description=(
            "Guided first-time discovery of cross-repo graph.relationships: "
            "machine inference, gap analysis, operator interview, draft report."
        ),
        scopes=["workspace"],
    ),
    PromptCatalogEntry(
        kind="graph-maintain",
        title="Workspace graph maintenance",
        description=(
            "Suggest, promote, and ingest cross-repo graph.relationships for GitNexus overlay and dependency maps."
        ),
        scopes=["workspace"],
    ),
]

_SCOPE_KINDS: dict[PromptScope, frozenset[PromptKind]] = {
    "workspace": frozenset(
        {
            "instructions",
            "session-start",
            "catalog-edit",
            "health-preflight",
            "sync-safe",
            "layout-change",
            "context-pack",
            "graph-discover",
            "graph-maintain",
        }
    ),
    "project": frozenset(
        {
            "instructions",
            "catalog-edit",
            "health-preflight",
            "sync-safe",
            "subagent-handoff",
            "layout-change",
            "context-pack",
        }
    ),
    "repo": frozenset(
        {
            "instructions",
            "sync-safe",
            "subagent-handoff",
            "layout-change",
            "repo-enrich",
            "context-pack",
        }
    ),
}


def list_catalog() -> list[PromptCatalogEntry]:
    """Return all registered prompt kinds."""
    return list(_CATALOG)


def kinds_for_scope(scope: PromptScope) -> list[PromptKind]:
    """Prompt kinds valid for a scope level."""
    return sorted(_SCOPE_KINDS[scope], key=lambda item: item)


def is_kind_allowed(kind: PromptKind, scope: PromptScope) -> bool:
    """True when kind can be emitted at scope."""
    return kind in _SCOPE_KINDS[scope]


def template_body(
    kind: PromptKind,
    scope: PromptScope,
    *,
    project_name: str | None = None,
    repo_name: str | None = None,
) -> str:
    """Return built-in prompt text for a kind and scope."""
    project_label = project_name or "<project>"
    repo_label = repo_name or "<repo>"
    templates: dict[PromptKind, str] = {
        "session-start": """You are operating a metagit-managed workspace. Run this checklist before changing code or disk layout.

1. `metagit appconfig show --format json` — workspace.path, dedupe, agent_mode.
2. `metagit workspace list -c <definition> --json` — projects, repos, clone/sync hints from index.
3. `metagit config info -c <definition>` — manifest summary.
4. `metagit search "<name-or-url>" -c <definition> --json` before creating projects or repos.
5. Prefer `metagit workspace project|repo add` over hand-editing repo lists; always `metagit config validate -c <definition>` after edits.""",
        "catalog-edit": """When registering or changing workspace catalog entries:

1. Search first: `metagit search "<name-or-url>" -c <definition> --json`.
2. Reuse existing workspace.projects[] and repos[] entries; do not clone into ad-hoc folders.
3. Add via catalog: `metagit workspace project add`, `metagit workspace repo add`, or `metagit project repo add --project <name>`.
4. Validate: `metagit config validate -c <definition>`.
5. Sync only with explicit approval: `metagit project sync --project <name>` (fetch/pull as operator directs).""",
        "health-preflight": """Before implementation work, run a workspace health pass:

1. `metagit workspace list -c <definition> --json` — missing clones, duplicate URLs, per-repo status in repos_index.
2. `metagit workspace repo list -c <definition> --project <name> --json` to narrow to one project.
3. Resolve blockers (missing clone, broken symlink mount, duplicate URL) before editing application code.
4. Re-run list after catalog or layout changes.""",
        "sync-safe": """Repository sync rules for metagit-managed workspaces:

- Default to fetch-only; use pull or clone only with explicit operator approval.
- Project batch: `metagit project sync --project <name>` after confirming scope with `metagit workspace repo list --json`.
- Inspect before sync: `metagit workspace list --json` for missing or dirty repos.
- Never delete canonical dedupe directories; project mounts are symlinks when workspace.dedupe is enabled.""",
        "subagent-handoff": """Hand off single-repo implementation to a subagent:

1. Controller stays at workspace/project scope; subagent receives repo-scoped instructions only.
2. `metagit workspace select --project <name>` or `metagit project select` when switching focus.
3. Pass the composed [REPO] layer (and project context) — not the full workspace controller stack unless required.
4. Subagent works only inside the resolved repo_path; no cross-project manifest edits unless escalated.""",
        "layout-change": """Rename or move projects/repos only through layout CLI:

1. Dry-run first: `metagit workspace project rename|repo rename|repo move --dry-run --json`.
2. Confirm disk_steps in JSON before applying without --dry-run.
3. `metagit config validate -c <definition>` after manifest updates.
4. `metagit workspace list --json` after layout changes complete.""",
        "context-pack": """## Tiered context pack (metagit)

At **session start**, always load **tier 0** workspace orientation (minimal tokens):

- **CLI:** `metagit context pack --tier 0 --json`
- **MCP:** `metagit_context_pack` (tier 0)

**Escalate to tier 1** for repositories in your **active scope** only—projects and repos you are actually changing or debugging in this task. Use tier 1 via `metagit context pack --tier 1 --json` or `metagit_context_pack` with tier 1 and repo/project scoping so deeper repo cards and maps apply where work is focused.

**Tier 2 (session-aware):** Adds a digest of git activity since the last session boundary (from `.metagit/sessions`), the active ``in_progress`` objective id when present, and whether the manifest changed—then bumps the session clock. Prefer **tier 2** when resuming multi-repo work rather than reloading an entire tier-1 pack blindly: `metagit context pack --tier 2 --json` / `metagit_context_pack` with tier ``2``.

**Token budgeting:** default to tier 0; add tier 1 only when needed; use tier 2 for resume/session deltas without replacing tier 1. Avoid loading full tier-1 packs for every repo—stay within the model context window.""",
        "repo-enrich": """Review this repository and enrich its workspace manifest entry using metagit CLI discovery only.

## 1. Baseline (manifest)
- `metagit workspace repo list -c <definition> --project <project> --json` — current entry for this repo.
- `metagit search "<repo>" -c <definition> --json` — confirm name, url, path, tags.
- `metagit appconfig show --format json` — resolve sync root (`workspace.path`).

## 2. Discover on disk
From the repo checkout under `{workspace.path}/<project>/<repo>/` (or resolved path from search):
- `metagit detect repository -p . -o json` — full detection payload (language, kind, frameworks, url hints).
- `metagit detect repo -p . -o yaml` — codebase analysis summary.
- `metagit detect repo_map -p . -o json` — directory map for structure-aware agent_instructions.
If the repo has its own `.metagit.yml`: `metagit detect repository -p . -o metagit` for local metadata (do not overwrite workspace file).

## 3. Provider discovery (when remote url is known)
- `metagit project source sync --provider github|gitlab --org|--user|--group ... --mode discover --no-apply`
- For idempotent catalog updates use `--mode additive --ensure --apply`; add `--refresh-metadata` to refresh topics/descriptions. Filters: `--ignore`, `--include-pattern`. Agent output: `--json`.
Use output to fill `url`, `source_provider`, `source_namespace`, `source_repo_id`, and provider tags when missing.

## 4. Merge into workspace.projects[].repos[]
Merge policy for the matching repo entry:
- Never remove or weaken `protected: true`.
- Fill only empty/null fields: `description`, `kind`, `language`, `language_version`, `package_manager`, `frameworks`, `url`, `branches`, `source_*`.
- Merge `tags` (add new keys; keep existing values on conflict unless the existing value is empty).
- Set `agent_instructions` only when blank; prefer repo-layer text from local `.metagit.yml` when appropriate.
- Do not rename the entry or change `path` unless `path` is missing and the on-disk location is canonical.

Persist by editing the umbrella `.metagit.yml` or `metagit workspace repo remove` + `metagit workspace repo add` with merged fields.

## 5. Validate
- `metagit config validate -c <definition>`
- `metagit workspace repo list --project <project> --json` — verify enriched fields.

Use `METAGIT_AGENT_MODE=true` for non-interactive runs; never use `detect repository --save` against the workspace file without explicit approval.""",
        "graph-discover": """Build an initial cross-repo relationship model for a metagit workspace. **Report first — do not apply** until the operator approves.

## 1. Inventory
- `metagit workspace list -c <definition> --json` — projects, repos, clone status.
- `metagit config info -c <definition>` — confirm whether `graph.relationships` is empty or partial.
- MCP `metagit_workspace_health_check` — surface missing clones before inferring edges.

## 2. Machine discovery (read-only)
For each workspace project:
- MCP `metagit_cross_project_dependencies` with `dependency_types: ["imports", "shared_config", "url_match", "declared", "ref"]` and `depth: 3`.
- `metagit config graph suggest -c <definition> --json --include-declared --min-confidence all` — candidates with evidence (do **not** pass `--apply`).

Group results into:
- **inferred_high** — import edges with file/manifest evidence
- **inferred_medium** — url_match, shared_config
- **inferred_low** — declared tags, ref-only hints
- **already_manual** — edges already in `graph.relationships`

## 3. Gap analysis
List project and repo pairs with **no** inferred or manual path. For each gap, note what code cannot see (ownership, docs, deploy order, shared secrets, API contracts).

## 4. Guided interview (operator)
For each gap (and any low-confidence inferred edge), ask the operator:
1. Source project/repo and target project/repo?
2. Relationship type: `depends_on`, `consumes`, `owns`, `documents`, `related`, or other?
3. Short `label` and one-line `description` for agents?
4. Optional `tags` (layer, team, environment)?

Use AskUserQuestion or an equivalent approval step. Do not invent semantic edges without answers.

## 5. Draft report (required output)
Emit a **Graph Discovery Report** with:
- `summary` — project/repo counts, candidate counts by confidence
- `proposed_machine_edges[]` — from suggest output (id, from, to, type, confidence, evidence)
- `proposed_manual_edges[]` — from interview (same shape as graph.relationships entries)
- `open_questions[]` — unresolved gaps
- `operations_preview` — merged patch ops JSON (from suggest + manual), **not applied**

Hand off apply/validate/ingest to `metagit prompt workspace -k graph-maintain` after operator sign-off.""",
        "graph-maintain": """Maintain durable cross-repo edges in `.metagit.yml` `graph.relationships` and sync them into GitNexus.

## 1. Discover inferred dependencies
- `metagit workspace list -c <definition> --json` — confirm projects/repos exist locally.
- MCP `metagit_cross_project_dependencies` per project (or CLI-equivalent scope) for imports, url_match, shared_config.
- `metagit config graph suggest -c <definition> --json` — candidates, evidence, and patch `operations`.

## 2. Promote with approval
- Review `candidates[]` confidence (`high` > `medium` > `low`) and `evidence`.
- Default promote: `imports`, `shared_config`, `url_match` at `--min-confidence medium`.
- Preview patch: `metagit config preview -c <definition> --file ops.json` using `operations` from suggest output.
- Apply: `metagit config graph suggest -c <definition> --apply` or MCP `metagit_apply_graph_relationships`.
- Validate: `metagit config validate -c <definition>`.

## 3. Export and ingest GitNexus overlay
- `metagit config graph export -c <definition> --format tool-calls` or MCP `metagit_export_workspace_graph_cypher`.
- Run schema statements once, then each Cypher statement via `gitnexus_cypher` or `./skills/metagit-gitnexus/scripts/ingest-workspace-graph.sh`.
- Pass `--gitnexus-repo` when the umbrella index name differs from manifest `name`.

## 4. Refresh per-repo code graphs
- `npx gitnexus analyze` on repos with `graph_status` stale/missing (see `metagit-gitnexus` skill).

## 5. GitNexus group sync (cross-index)
- `metagit gitnexus group sync -c <definition> --json` or MCP `metagit_gitnexus_group_sync` after repos are indexed.
- Then `npx gitnexus group query <group> "…"` / `group impact` for cross-repo symbol analysis.

Safety: do not promote edges without evidence; do not overwrite existing manual relationships; fetch operator approval before `--apply`.""",
    }
    if kind == "instructions":
        return ""
    body = templates.get(kind, "")
    if scope == "project" and kind in {
        "catalog-edit",
        "health-preflight",
        "subagent-handoff",
        "context-pack",
    }:
        body += f"\n\nFocused project: {project_label}."
    if scope == "repo":
        if kind == "sync-safe":
            body += f"\n\nFocused repo: {project_label}/{repo_label}."
        elif kind == "subagent-handoff":
            body += (
                f"\n\nYou are the subagent for {project_label}/{repo_label}. "
                "Follow [REPO] instructions below; escalate cross-repo issues to the controller."
            )
        elif kind == "layout-change":
            body += f"\n\nTarget: {project_label}/{repo_label}."
        elif kind == "repo-enrich":
            body += f"\n\nTarget repo: {project_label}/{repo_label}. Emit merged YAML for the repos[] entry when done."
        elif kind == "context-pack":
            body += (
                f"\n\nActive-scope focus: {project_label}/{repo_label}. "
                "Use tier 1 for this repo when it is in scope; otherwise stay on tier 0."
            )
    return body.strip()
