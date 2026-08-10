# Durable Graph + Suggest UX/Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `graph.relationships` durable and agent-maintainable, fix `-c` vs `--workspace-root` confusion, add verbose suggest output, and ensure import/suggest walks never enter venvs, caches, or gitignored trees.

**Architecture:** Add a shared ignore-aware repo walker (scaffold denylist + nested `.gitignore`) and use it from `ImportHintScanner`. Extend `GraphRelationship` with `status`/`provenance` and validation for required `id` + endpoint existence. Teach `config graph suggest|export` leaf `-c`, human `--verbose` summaries, and report-only `stale_manual[]`. Update prompts/skills/docs in the same ship.

**Tech Stack:** Python 3, Pydantic, Click, existing `parse_gitignore` / `should_ignore_path`, pytest, `uv run`, Taskfile (`generate:schema`, `skills:sync`, `qa:prepush`).

**Design:** [2026-07-28-durable-graph-suggest-design.md](../specs/2026-07-28-durable-graph-suggest-design.md)

## Global Constraints

- Scaffold denylist **always** applies, even if a path is tracked / not gitignored.
- `.gitignore` must be honored per managed repo (nested, prune during walk — never full `rglob` then filter).
- Leaf `-c` = `.metagit.yml`; `--workspace-root` = scan/checkout root; global `metagit -c` remains appconfig.
- Stale edges are **report-only** in v1 (no `--mark-stale`).
- No first-class durable `confidence`; evidence stays in suggest result + `metadata` on apply.
- Do not expand into Atlas / semantic ownership.
- Run `task qa:prepush` then `task gitnexus:analyze` before claiming done.
- Prefer feature branch `feat/durable-graph-suggest-ux`.

## Out of scope

`--mark-stale`, constrained `type` enum, first-class durable `confidence`, full shared walker adoption by `WorkspaceSearchService` (optional reuse of scaffold constant only).

## File map (create)

| Path | Responsibility |
|------|----------------|
| `src/metagit/core/utils/scaffold_paths.py` | Shared `_SCAFFOLD_PATH_SEGMENTS` / helper `path_has_scaffold_segment` |
| `src/metagit/core/utils/repo_walk.py` | Ignore-aware `iter_repo_files` + `RepoWalkStats` |
| `src/metagit/core/config/graph_validation.py` | Validate relationship ids + endpoints against workspace |
| `tests/core/utils/test_repo_walk.py` | Walker scaffold + gitignore tests |
| `tests/core/mcp/services/test_import_hint_scanner_ignore.py` | Terraform scan skips venv/gitignore |
| `tests/core/config/test_graph_validation.py` | id / endpoint / status rules |
| `tests/cli/commands/test_config_graph_cli.py` | Leaf `-c`, `--verbose` |

## File map (modify)

| Path | Change |
|------|--------|
| `src/metagit/core/mcp/services/workspace_search.py` | Import scaffold set from `scaffold_paths` |
| `src/metagit/core/mcp/services/import_hint_scanner.py` | Use `iter_repo_files` for `*.tf`; expose last walk stats |
| `src/metagit/core/config/graph_models.py` | `status`, `provenance`; keep `id` optional on model, validate externally |
| `src/metagit/core/config/graph_suggest.py` | Scan stats, `stale_manual`, apply `status`/`provenance` |
| `src/metagit/cli/commands/config.py` | Leaf `-c` on suggest/export; `--verbose`; human summary |
| `src/metagit/core/prompt/catalog.py` | Lifecycle + `-c` vs `--workspace-root` + `stale_manual` |
| `docs/reference/metagit-config.md` | Flag semantics + new fields |
| `skills/metagit-graph-maintain/**`, `skills/metagit-cli/**`, scripts | Flag note + lifecycle; then `task skills:sync` |
| `schemas/metagit_config.schema.json` + docs copies | Via `task generate:schema` |
| `CHANGELOG.md`, `.mex/ROUTER.md` | Record ship |

---

### Task 1: Shared scaffold paths + ignore-aware repo walker

**Files:**
- Create: `src/metagit/core/utils/scaffold_paths.py`
- Create: `src/metagit/core/utils/repo_walk.py`
- Modify: `src/metagit/core/mcp/services/workspace_search.py` (import shared scaffold set)
- Test: `tests/core/utils/test_repo_walk.py`

**Interfaces:**
- Produces: `SCAFFOLD_PATH_SEGMENTS: frozenset[str]`, `path_has_scaffold_segment(file_path: str) -> bool`
- Produces: `RepoWalkStats(dirs_pruned: int, files_skipped_gitignore: int, files_yielded: int)`
- Produces: `iter_repo_files(root: Path, *, suffix: str | None = None, max_files: int | None = None) -> tuple[list[Path], RepoWalkStats]`

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python
"""Tests for ignore-aware repo file walking."""

from __future__ import annotations

from pathlib import Path

from metagit.core.utils.repo_walk import iter_repo_files


def test_iter_repo_files_skips_node_modules_and_venv(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "modules").mkdir(parents=True)
    (root / "modules" / "ok.tf").write_text('source = "../other"', encoding="utf-8")
    (root / "node_modules" / "pkg").mkdir(parents=True)
    (root / "node_modules" / "pkg" / "bad.tf").write_text("x", encoding="utf-8")
    (root / ".venv" / "lib").mkdir(parents=True)
    (root / ".venv" / "lib" / "bad.tf").write_text("x", encoding="utf-8")

    files, stats = iter_repo_files(root, suffix=".tf")
    rels = {str(p.relative_to(root)) for p in files}
    assert rels == {"modules/ok.tf"}
    assert stats.dirs_pruned >= 2


def test_iter_repo_files_honors_gitignore(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "keep").mkdir(parents=True)
    (root / "keep" / "a.tf").write_text("x", encoding="utf-8")
    (root / "secret").mkdir(parents=True)
    (root / "secret" / "b.tf").write_text("x", encoding="utf-8")
    (root / ".gitignore").write_text("secret/\n", encoding="utf-8")

    files, stats = iter_repo_files(root, suffix=".tf")
    rels = {str(p.relative_to(root)) for p in files}
    assert rels == {"keep/a.tf"}
    assert stats.files_skipped_gitignore >= 1 or stats.dirs_pruned >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/utils/test_repo_walk.py -v`  
Expected: FAIL (module not found)

- [ ] **Step 3: Implement scaffold_paths + repo_walk**

`scaffold_paths.py` — move the frozenset currently in `workspace_search.py` here (same members). Export `path_has_scaffold_segment`.

`repo_walk.py` — `os.walk(..., topdown=True, followlinks=False)`:
1. Drop dirnames in `SCAFFOLD_PATH_SEGMENTS`; increment `dirs_pruned`.
2. Load/accumulate `.gitignore` patterns from repo root and each visited dir via `parse_gitignore`.
3. Skip dirs/files matching `should_ignore_path`; count skips.
4. If `suffix` set, only yield files ending with that suffix.
5. Stop yielding when `max_files` reached (still OK to stop early).

- [ ] **Step 4: Point workspace_search at shared scaffold module**

Replace local `_SCAFFOLD_PATH_SEGMENTS` with import from `metagit.core.utils.scaffold_paths`. Keep `_path_has_scaffold_segment` as a thin wrapper or call the shared helper.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/core/utils/test_repo_walk.py tests/core/mcp/services/ -k workspace_search -v --maxfail=5`  
Expected: PASS for new tests; no regressions in search ignore behavior.

- [ ] **Step 6: Commit**

```bash
git add src/metagit/core/utils/scaffold_paths.py src/metagit/core/utils/repo_walk.py \
  src/metagit/core/mcp/services/workspace_search.py tests/core/utils/test_repo_walk.py
git commit -m "$(cat <<'EOF'
feat: add ignore-aware repo walker with scaffold denylist

EOF
)"
```

---

### Task 2: Wire ImportHintScanner to the walker

**Files:**
- Modify: `src/metagit/core/mcp/services/import_hint_scanner.py`
- Test: `tests/core/mcp/services/test_import_hint_scanner_ignore.py`

**Interfaces:**
- Consumes: `iter_repo_files(root, suffix=".tf", max_files=40)`
- Produces: `ImportHintScanner.last_walk_stats: RepoWalkStats | None` after `scan_repo`

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python
"""Import hint scanner must not walk node_modules / gitignored trees."""

from __future__ import annotations

from pathlib import Path

from metagit.core.mcp.services.import_hint_scanner import ImportHintScanner


def test_terraform_scan_skips_node_modules(tmp_path: Path) -> None:
    root = tmp_path / "infra"
    other = tmp_path / "modules"
    other.mkdir()
    (other / ".git").mkdir()
    (root / "live").mkdir(parents=True)
    (root / "live" / "main.tf").write_text(
        f'source = "{other.as_posix()}"\n',
        encoding="utf-8",
    )
    (root / "node_modules" / "x").mkdir(parents=True)
    (root / "node_modules" / "x" / "junk.tf").write_text(
        'source = "/should/not/matter"\n',
        encoding="utf-8",
    )
    path_map = {str(other.resolve()): "repo:alpha/modules"}
    scanner = ImportHintScanner()
    hints = scanner.scan_repo(str(root), path_map)
    evidence = " ".join(e for h in hints for e in h.get("evidence", []))
    assert "node_modules" not in evidence
    assert scanner.last_walk_stats is not None
    assert scanner.last_walk_stats.dirs_pruned >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/mcp/services/test_import_hint_scanner_ignore.py -v`  
Expected: FAIL (`rglob` still used / no `last_walk_stats`)

- [ ] **Step 3: Replace `rglob` in `_scan_terraform_modules`**

```python
from metagit.core.utils.repo_walk import RepoWalkStats, iter_repo_files

class ImportHintScanner:
    def __init__(self) -> None:
        self.last_walk_stats: RepoWalkStats | None = None

    def _scan_terraform_modules(...):
        files, stats = iter_repo_files(root, suffix=".tf", max_files=40)
        self.last_walk_stats = stats
        for tf_file in files:
            ...
```

Reset `last_walk_stats = None` at start of `scan_repo`; accumulate stats if multiple walks later.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/mcp/services/test_import_hint_scanner_ignore.py tests/core/config/test_graph_suggest.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/mcp/services/import_hint_scanner.py \
  tests/core/mcp/services/test_import_hint_scanner_ignore.py
git commit -m "$(cat <<'EOF'
fix: skip venv and gitignored paths in terraform import scan

EOF
)"
```

---

### Task 3: Leaf `-c` on graph suggest/export + `--verbose` summary

**Files:**
- Modify: `src/metagit/cli/commands/config.py` (`config_graph_export`, `config_graph_suggest`)
- Modify: `src/metagit/core/config/graph_suggest.py` (optional `scan_stats` on `GraphSuggestResult`)
- Test: `tests/cli/commands/test_config_graph_cli.py`

**Interfaces:**
- Produces: leaf options `--config-path/-c` on suggest & export (override `ctx.obj["config_path"]` when set)
- Produces: `--verbose` on suggest; logger summary including roots, candidate counts, prune stats
- Produces: `GraphSuggestResult.scan_stats: dict[str, int] | None` with keys `dirs_pruned`, `files_skipped_gitignore`, `files_yielded` (aggregated)

- [ ] **Step 1: Write the failing CLI tests**

```python
#!/usr/bin/env python
"""CLI tests for config graph suggest/export leaf -c and verbose."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _minimal_manifest(path: Path) -> None:
    path.write_text(
        "name: demo\nkind: umbrella\nworkspace:\n  projects:\n"
        "    - name: p\n      repos: []\n",
        encoding="utf-8",
    )


def test_graph_suggest_accepts_leaf_config_path(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / ".metagit.yml"
    _minimal_manifest(manifest)
    # Point appconfig workspace.path at tmp_path if required by CLI bootstrap;
    # follow patterns in tests/cli/commands/test_context.py for env workspace root.
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["config", "graph", "suggest", "-c", str(manifest), "--json"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "candidates" in result.output


def test_graph_suggest_verbose_prints_summary(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    _minimal_manifest(manifest)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["config", "graph", "suggest", "-c", str(manifest), "--verbose", "--json"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    # Summary goes to logger/stderr or non-JSON lines; assert key phrases appear
    combined = result.output + (result.stderr or "")
    assert "candidates" in combined.lower() or "Graph suggest" in combined
```

Adapt fixture bootstrap to match existing CLI tests (workspace env / appconfig). If full invoke is heavy, unit-test the summary helper and a thinner Click command test.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/cli/commands/test_config_graph_cli.py -v`  
Expected: FAIL (`No such option '-c'`)

- [ ] **Step 3: Implement leaf `-c` and `--verbose`**

Mirror `config_validate`:

```python
@click.option("--config-path", "-c", default=None, help="Path to the metagit configuration file")
```

At start of suggest/export handlers:

```python
if config_path:
    ctx.obj["config_path"] = config_path
target = ctx.obj["config_path"]
```

Add `--verbose` flag. When verbose (or when not `--json`), call a small helper `_emit_graph_suggest_summary(logger, result, *, config_path, workspace_root)` printing:
- manifest path, workspace root
- candidate count by confidence
- `already_manual` count, `skipped_low_confidence`
- scan_stats prune counts
- apply outcome if present

Default without `--json`: print the human summary **and** a short candidate list (id, from→to, type, confidence), not a raw full JSON dump. With `--json`: emit JSON on stdout; verbose summary via logger only.

Thread walk stats from dependency/import scanning into `GraphSuggestResult.scan_stats` (aggregate `ImportHintScanner.last_walk_stats` across repos inside suggest, or attach from cross-project service if easier).

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/cli/commands/test_config_graph_cli.py tests/core/config/test_graph_suggest.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/cli/commands/config.py src/metagit/core/config/graph_suggest.py \
  tests/cli/commands/test_config_graph_cli.py
git commit -m "$(cat <<'EOF'
feat: accept leaf -c and --verbose on config graph suggest/export

EOF
)"
```

---

### Task 4: Docs/skills/scripts flag semantics

**Files:**
- Modify: `docs/reference/metagit-config.md`
- Modify: `skills/metagit-graph-maintain/SKILL.md` + `scripts/maintain-graph.sh`
- Modify: `skills/metagit-cli/SKILL.md` (graph rows)
- Modify: `skills/metagit-gitnexus/SKILL.md` + ingest script if it places `-c` wrong
- Run: `task skills:sync` (copies into `.agents/skills` and `src/metagit/data/skills`)

**Interfaces:**
- Produces: documented rule — trailing `-c` on suggest/export is valid; `-c` = manifest; `--workspace-root` = scan root; global `metagit -c` = appconfig

- [ ] **Step 1: Update metagit-config.md Manual graph section**

Add a short “CLI flags” note after the suggest examples:

```markdown
### CLI flags

- `metagit config graph suggest|export -c .metagit.yml` — path to the **manifest** (leaf or `metagit config -c … graph …`).
- `--workspace-root` — checkout root used to **scan** inferred deps (default: appconfig `workspace.path`).
- Global `metagit -c metagit.config.yaml` configures **appconfig**, not `.metagit.yml`.
- Prefer `metagit config graph suggest -c .metagit.yml --verbose` when debugging empty candidates.
```

Keep existing example commands that put `-c` after `suggest` (now valid after Task 3).

- [ ] **Step 2: Update graph-maintain skill + maintain-graph.sh**

In SKILL.md, add the same one-liner under Maintenance workflow. Ensure script uses:

```bash
args=(config graph suggest -c "$config_path" --min-confidence "$min_confidence" --json)
```

(already correct once leaf `-c` exists).

- [ ] **Step 3: Sync packaged skills**

Run: `task skills:sync`  
Expected: `.agents/skills` and `src/metagit/data/skills` copies updated.

- [ ] **Step 4: Commit**

```bash
git add docs/reference/metagit-config.md skills/ .agents/skills/ src/metagit/data/skills/
git commit -m "$(cat <<'EOF'
docs: clarify config graph -c vs --workspace-root for agents

EOF
)"
```

---

### Task 5: Durable fields + validation (`id`, endpoints, status, provenance)

**Files:**
- Modify: `src/metagit/core/config/graph_models.py`
- Create: `src/metagit/core/config/graph_validation.py`
- Modify: `src/metagit/cli/commands/config.py` (`config_validate`)
- Modify: `src/metagit/core/config/graph_suggest.py` (`_candidate_value` / apply)
- Modify: `examples/metagit-rewrite/.metagit.yml` if needed (already has `id`)
- Test: `tests/core/config/test_graph_validation.py`
- Run: `task generate:schema`

**Interfaces:**
- Produces: `GraphRelationship.status: Literal["active","deprecated","proposed"] = "active"`
- Produces: `GraphRelationship.provenance: Literal["manual","promoted","imported"] = "manual"`
- Produces: `validate_graph_relationships(config: MetagitConfig) -> list[str]` (empty = ok)
- Produces: apply sets `status="active"`, `provenance="promoted"`; generates `id` if missing via existing candidate id logic

- [ ] **Step 1: Write failing validation tests**

```python
#!/usr/bin/env python
"""Tests for graph.relationships validation."""

from __future__ import annotations

from metagit.core.config.graph_models import GraphEndpoint, GraphRelationship, WorkspaceGraph
from metagit.core.config.graph_validation import validate_graph_relationships
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _config_with_rel(**rel_kwargs) -> MetagitConfig:
    base = dict(
        id="ok",
        from_endpoint=GraphEndpoint(project="alpha", repo="api"),
        to=GraphEndpoint(project="beta", repo="worker"),
        type="depends_on",
    )
    base.update(rel_kwargs)
    return MetagitConfig(
        name="ws",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(name="alpha", repos=[ProjectPath(name="api", path="a")]),
                WorkspaceProject(name="beta", repos=[ProjectPath(name="worker", path="b")]),
            ]
        ),
        graph=WorkspaceGraph(relationships=[GraphRelationship(**base)]),
    )


def test_blank_id_is_invalid() -> None:
    cfg = _config_with_rel(id=None)
    issues = validate_graph_relationships(cfg)
    assert any("id" in i.lower() for i in issues)


def test_unknown_project_is_invalid() -> None:
    cfg = _config_with_rel(
        from_endpoint=GraphEndpoint(project="nope", repo="api"),
    )
    issues = validate_graph_relationships(cfg)
    assert any("nope" in i for i in issues)


def test_status_and_provenance_defaults() -> None:
    rel = GraphRelationship(
        id="x",
        from_endpoint=GraphEndpoint(project="alpha"),
        to=GraphEndpoint(project="beta"),
    )
    assert rel.status == "active"
    assert rel.provenance == "manual"
```

- [ ] **Step 2: Run tests — expect fail**

Run: `uv run pytest tests/core/config/test_graph_validation.py -v`

- [ ] **Step 3: Implement models + validator**

In `graph_models.py` add fields with `Literal` types and defaults. Keep `id: Optional[str]` on the model so load still works; **`validate_graph_relationships`** requires non-blank `id` when `graph.relationships` is non-empty.

Validator builds `project -> set(repo names)` from `config.workspace.projects`. Allow missing `repo` (project-level edges). Reject unknown project/repo. Do **not** require the synthetic `local` project unless it appears in workspace.

Wire into `config_validate` after successful load:

```python
from metagit.core.config.graph_validation import validate_graph_relationships
issues = validate_graph_relationships(result)
if issues:
    for issue in issues:
        logger.error(issue)
    ctx.abort()
```

Also call validator inside suggest apply before save; surface errors on `GraphSuggestApplyResult.validation_errors`.

Update `_candidate_value`:

```python
return GraphRelationship(
    id=candidate.id,
    ...
    status="active",
    provenance="promoted",
    metadata=dict(candidate.metadata),
).model_dump(mode="json", by_alias=True)
```

- [ ] **Step 4: Regenerate schema**

Run: `task generate:schema`  
Expected: `schemas/metagit_config.schema.json` and docs copies include `status` / `provenance`.

- [ ] **Step 5: Run tests + fixtures**

Run: `uv run pytest tests/core/config/test_graph_validation.py tests/core/config/test_graph_suggest.py -v`  
Run: `uv run metagit config validate -c .metagit.yml` and example manifests listed in `scripts/manifest-fixtures.yml`.

- [ ] **Step 6: Commit**

```bash
git add src/metagit/core/config/graph_models.py src/metagit/core/config/graph_validation.py \
  src/metagit/cli/commands/config.py src/metagit/core/config/graph_suggest.py \
  tests/core/config/test_graph_validation.py schemas/ docs/reference/schemas/ \
  docs/reference/metagit-config.full-example.yml
git commit -m "$(cat <<'EOF'
feat: validate graph relationship ids, endpoints, and lifecycle fields

EOF
)"
```

---

### Task 6: `stale_manual[]` + prompt/skill lifecycle wording

**Files:**
- Modify: `src/metagit/core/config/graph_suggest.py`
- Modify: `src/metagit/core/prompt/catalog.py` (`graph-discover`, `graph-maintain`)
- Modify: `skills/metagit-graph-maintain/SKILL.md` (+ sync)
- Modify: `docs/reference/metagit-config.md`
- Test: extend `tests/core/config/test_graph_suggest.py`

**Interfaces:**
- Produces: `GraphSuggestResult.stale_manual: list[str]` — stable ids or `from->to:type` keys for active manual edges with no supporting inferred edge under the current scan
- Produces: prompts mention `status`/`provenance`, review `stale_manual`, prefer `--verbose`

- [ ] **Step 1: Write failing stale test**

```python
def test_suggest_reports_stale_manual_edges(tmp_path: Path) -> None:
    config, workspace_root = _workspace_fixture(tmp_path)
    config.graph = {
        "relationships": [
            {
                "id": "orphan-edge",
                "from": {"project": "alpha", "repo": "api"},
                "to": {"project": "beta", "repo": "worker"},
                "type": "depends_on",
                "status": "active",
                "provenance": "manual",
            }
        ]
    }
    # Ensure no package.json import that would support this edge (remove worker package.json)
    Path(workspace_root, "beta", "worker", "package.json").unlink(missing_ok=True)
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {}
    service = GraphRelationshipSuggestService(
        dependency_service=CrossProjectDependencyService(registry=registry)
    )
    result = service.suggest(config, workspace_root, min_confidence="all", include_declared=True)
    assert any("orphan-edge" in item for item in result.stale_manual)
```

Adjust fixture so the orphan truly has no url_match/import support (may need distinct URLs on repos).

- [ ] **Step 2: Implement stale detection**

After collecting inferred edges and existing manual relationships:
- Build set of keys for inferred edges (same keying as `already_manual`).
- For each manual rel with `status != "deprecated"`, if its key not in inferred set and not matched by a candidate, append to `stale_manual` (prefer `rel.id` else synthetic key).

Include `stale_manual` in verbose summary and JSON payload.

- [ ] **Step 3: Update prompts**

In `graph-maintain` template, add:

```text
## Lifecycle
- Promoted edges should have status=active and provenance=promoted.
- Review suggest `stale_manual[]` (report-only): confirm with operator before editing/removing.
- Use `--verbose` when candidates are empty to confirm scan roots and ignore prune counts.
- `-c` selects the manifest; `--workspace-root` selects the checkout scan root.
```

Mirror briefly in `graph-discover` and the graph-maintain skill.

- [ ] **Step 4: Sync skills + run tests**

Run: `task skills:sync`  
Run: `uv run pytest tests/core/config/test_graph_suggest.py tests/core/prompt/ -v`

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/config/graph_suggest.py src/metagit/core/prompt/catalog.py \
  skills/ .agents/skills/ src/metagit/data/skills/ docs/reference/metagit-config.md \
  tests/core/config/test_graph_suggest.py
git commit -m "$(cat <<'EOF'
feat: report stale manual graph edges and document lifecycle for agents

EOF
)"
```

---

### Task 7: Closeout (CHANGELOG, ROUTER, QA, GitNexus)

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `.mex/ROUTER.md` (project state bullet)
- Optional: `.mex/patterns/graph-suggest-maintain.md` if no pattern exists

- [ ] **Step 1: Changelog entry** under Unreleased — leaf `-c`, verbose suggest, ignore-aware scan, durable status/provenance, validation, stale_manual.

- [ ] **Step 2: Update ROUTER current state** with one bullet pointing at the design + this plan.

- [ ] **Step 3: Run full gate**

Run: `task qa:prepush`  
Fix failures until green.

- [ ] **Step 4: Refresh GitNexus**

Run: `task gitnexus:analyze`

- [ ] **Step 5: Final commit**

```bash
git add CHANGELOG.md .mex/ROUTER.md .mex/patterns/
git commit -m "$(cat <<'EOF'
docs: record durable graph suggest UX ship in changelog and router

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Leaf `-c` on suggest/export | 3 |
| Docs/skills flag clarification | 4, 6 |
| `--verbose` + human summary | 3 |
| Scaffold denylist always-on | 1, 2 |
| Nested `.gitignore` prune-during-walk | 1, 2 |
| Required `id` validation | 5 |
| Endpoint validation | 5 |
| `status` / `provenance` + apply defaults | 5 |
| `stale_manual[]` report-only | 6 |
| Prompt/skill lifecycle | 6 |
| Schema regenerate | 5 |
| QA + GitNexus closeout | 7 |

## Deferred (do not implement in this plan)

- `--mark-stale`
- Constrained `type` enum
- First-class durable `confidence`
- Full walker adoption inside `WorkspaceSearchService` (scaffold constant shared only)
