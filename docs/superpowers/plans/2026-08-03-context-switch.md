# Context Switch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `metagit context switch` (CLI), prompt kind `context-switch`, MCP `metagit_context_switch`, and docs/skills/modality so agents can bootstrap a project/repo with pack + prompt + objective + shell-eval env in one call.

**Architecture:** New `ContextSwitchService` composes `ProjectContextService.switch`, `ContextPackService.pack`, `PromptService.emit`, and `ObjectiveService.upsert_partial` (same style as `SessionBeginService`). CLI and MCP are thin wrappers. Lean `metagit_project_context_switch` stays unchanged.

**Tech Stack:** Python 3, Pydantic, Click, MCP runtime, pytest, `shlex.quote` for shell exports.

**Design:** [2026-08-03-context-switch-design.md](../specs/2026-08-03-context-switch-design.md)

## Global Constraints

- Compose on `ProjectContextService`; do not fork session persistence.
- Keep env keys `METAGIT_WORKSPACE_ROOT`, `METAGIT_PROJECT`, `METAGIT_PROJECT_REPOS`.
- Default bootstrap: tier 2 + `context-switch` prompt + objective; opt-outs via flags.
- Default CLI stdout = shell `export` lines only; pack/prompt on stderr; `--json` for full envelope.
- Objective upsert failures are hard failures when objectives are included.
- 2-space indent; type hints; `#!/usr/bin/env python` on new files.
- Modality id `context_switch`; sync skills via `task skills:sync` after editing public skill sources.
- Before hand-off: `task qa:prepush` then `task gitnexus:analyze`; update `.mex/ROUTER.md`.
- Commit messages: `feat:` for additive surfaces.

## File map

| Path | Responsibility |
|------|----------------|
| Modify: `src/metagit/core/prompt/models.py` | Add `context-switch` to `PromptKind` |
| Modify: `src/metagit/core/prompt/catalog.py` | Catalog entry + workspace scope + template |
| Modify: `src/metagit/core/context/models.py` | `ContextSwitchResult` |
| Create: `src/metagit/core/context/context_switch_service.py` | Orchestrator |
| Modify: `src/metagit/cli/commands/context.py` | `context switch` command |
| Modify: `src/metagit/core/mcp/tool_registry.py` | Register tool name |
| Modify: `src/metagit/core/mcp/runtime.py` | Schema + dispatch |
| Create: `tests/core/context/test_context_switch_service.py` | Service tests |
| Create/modify: `tests/cli/commands/test_context.py` | CLI switch tests |
| Modify: `tests/core/mcp/test_runtime.py` | MCP tool tests |
| Create: `docs/reference/context-switch.md` | Operator + tag conventions |
| Modify: skills `metagit-context-pack`, `metagit-workspace-scope` (under `skills/` then sync) |
| Modify: `scripts/modality-parity.yml` | `context_switch` feature |
| Modify: `CHANGELOG.md`, `.mex/ROUTER.md`, `mkdocs.yml` (nav entry), `docs/agents.md` |

---

### Task 1: Prompt kind `context-switch`

**Files:**
- Modify: `src/metagit/core/prompt/models.py`
- Modify: `src/metagit/core/prompt/catalog.py`
- Test: extend existing prompt tests if present, or add `tests/core/prompt/test_catalog_context_switch.py`

**Interfaces:**
- Produces: `PromptKind` includes `"context-switch"`; workspace scope allows it; `template_body("context-switch", ...)` returns switch checklist

- [ ] **Step 1: Write failing test**

```python
#!/usr/bin/env python
"""Prompt catalog coverage for context-switch kind."""

from __future__ import annotations

from metagit.core.prompt.catalog import is_kind_allowed, template_body
from metagit.core.prompt.models import PromptKind


def test_context_switch_kind_is_literal_member() -> None:
  assert "context-switch" in PromptKind.__args__  # type: ignore[attr-defined]


def test_context_switch_allowed_for_workspace() -> None:
  assert is_kind_allowed("context-switch", "workspace") is True


def test_context_switch_template_mentions_env_and_objective() -> None:
  body = template_body("context-switch", "workspace", workspace_root="/tmp/ws")
  assert "METAGIT_PROJECT" in body
  assert "objective" in body.lower()
```

Note: if `PromptKind` is a `Literal` alias, use `get_args(PromptKind)` from `typing` instead of `.__args__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/prompt/test_catalog_context_switch.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement**

In `models.py`, add `"context-switch"` to the `PromptKind` Literal list (after `"session-start"`).

In `catalog.py`:
1. Add `PromptCatalogEntry(kind="context-switch", title="Workspace context switch", description="Mid-session project/repo bootstrap checklist after metagit context switch.", scopes=["workspace"])`.
2. Add `"context-switch"` to `_SCOPE_KINDS["workspace"]`.
3. Add template in `template_body` dict:

```text
You are switching Metagit workspace context mid-session (not a cold session-start).

1. Trust env exports already set (METAGIT_PROJECT, METAGIT_WORKSPACE_ROOT, METAGIT_WORKING_DIR, optional METAGIT_HERMES_PROFILE).
2. Use the attached/available context pack as current scope; do not re-run a full cold session-start checklist unless the pack is missing.
3. If an objective id was created for this switch (ctx-*), treat it as the active work item unless superseded.
4. Prefer search/sync scoped to the switched project; avoid unrelated catalog mutations.
5. For lean switch-only (no pack/objective), MCP metagit_project_context_switch remains available.
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/core/prompt/test_catalog_context_switch.py -v`  
Also: `uv run metagit prompt workspace -k context-switch --text-only` (needs a manifest in cwd or pass `-c`).

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/prompt/models.py src/metagit/core/prompt/catalog.py tests/core/prompt/test_catalog_context_switch.py
git commit -m "$(cat <<'EOF'
feat: add context-switch prompt kind for workspace scope

EOF
)"
```

---

### Task 2: `ContextSwitchResult` + `ContextSwitchService`

**Files:**
- Modify: `src/metagit/core/context/models.py` (add model near `SessionBeginResult`)
- Create: `src/metagit/core/context/context_switch_service.py`
- Test: `tests/core/context/test_context_switch_service.py`

**Interfaces:**
- Consumes: `ProjectContextService.switch`, `ContextPackService.pack`, `PromptService.emit`, `ObjectiveService.upsert_partial`, `find_project` / `find_repo`
- Produces:

```python
class ContextSwitchResult(BaseModel):
  ok: bool = True
  error: Optional[str] = None
  project_name: str = ""
  repo_name: Optional[str] = None
  switch: Optional[dict[str, Any]] = None  # ProjectContextBundle dump or embed
  pack: Optional[ContextPackResult] = None
  prompt: Optional[str] = None
  prompt_kind: Optional[str] = None
  objective_id: Optional[str] = None
  env: dict[str, str] = Field(default_factory=dict)
  warnings: list[str] = Field(default_factory=list)

class ContextSwitchService:
  def switch(
    self,
    *,
    config: MetagitConfig,
    config_path: str,
    workspace_root: str,   # sync root for pack / ProjectContextService
    session_root: str,     # objectives / SessionStore
    definition_root: str,
    project_name: str,
    repo_name: Optional[str] = None,
    tier: int = 2,
    include_pack: bool = True,
    include_prompt: bool = True,
    include_objective: bool = True,
    prompt_kind: str = "context-switch",
    max_tokens: Optional[int] = None,
  ) -> ContextSwitchResult
```

Tag merge helpers (private methods on the service):
- Read `project.tags` and primary repo `tags` (dict[str,str]).
- Map `hermes_profile` → `METAGIT_HERMES_PROFILE`, `working_dir` → `METAGIT_WORKING_DIR`, `default_task_namespace` → `METAGIT_DEFAULT_TASK_NAMESPACE`.
- Repo tags override project tags when `repo_name` is set.
- Always set `METAGIT_AGENT_MODE=true` on the returned `env` map.
- If `METAGIT_WORKING_DIR` still unset: use `bundle.suggested_cwd` if present, else first repo path from switch env `METAGIT_PROJECT_REPOS`.

Objective id: `ctx-` + UTC timestamp like `ctx-20260803T211500Z` (use `datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")`). Title: `Context: {project}` or `Context: {project}/{repo}`. `repos`: list with resolved path when available.

Session root vs sync root: pass `session_root` into `ObjectiveService` and into `ProjectContextService.switch` as `workspace_root` **only if** existing MCP uses `status.root_path` for both — check `SessionBeginService` / MCP dispatch. Prefer: `ProjectContextService.switch(..., workspace_root=session_root)` if SessionStore lives at session root; pack uses `workspace_root=sync_root` and `session_root=session_root` like `pack_cmd`. Read `_context_paths` and MCP project context dispatch before wiring — match MCP’s current `workspace_root=status.root_path` for switch so session files stay consistent with `metagit_project_context_switch`.

- [ ] **Step 1: Write failing service tests** (tmp_path fixture with mini umbrella manifest + sync dirs)

Cover at minimum:
1. Unknown project → `ok=False`, `error=="project_not_found"`.
2. Known project with `--no-pack --no-prompt --no-objective` still returns env with `METAGIT_PROJECT` and `METAGIT_AGENT_MODE`.
3. Full bootstrap creates objective id starting with `ctx-` and non-empty prompt/pack when services succeed (mock pack/prompt if disk-heavy).
4. Tag `hermes_profile: attune` on project exports `METAGIT_HERMES_PROFILE=attune`.

Example skeleton:

```python
#!/usr/bin/env python
"""Unit tests for ContextSwitchService."""

from __future__ import annotations

from pathlib import Path

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.context.context_switch_service import ContextSwitchService


def _write_workspace(tmp_path: Path) -> tuple[str, str, str]:
  sync = tmp_path / "sync"
  (sync / "attune" / "attune").mkdir(parents=True)
  manifest = tmp_path / ".metagit.yml"
  manifest.write_text(
    "\n".join(
      [
        "name: ws",
        "kind: umbrella",
        "workspace:",
        "  projects:",
        "    - name: attune",
        "      tags:",
        "        hermes_profile: attune",
        "      repos:",
        "        - name: attune",
        "          url: https://example.com/attune.git",
        "          path: ./attune",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  return str(manifest), str(sync), str(tmp_path)


def test_switch_unknown_project(tmp_path: Path) -> None:
  manifest, sync, session = _write_workspace(tmp_path)
  config = MetagitConfigManager(manifest).load_config()
  assert not isinstance(config, Exception)
  result = ContextSwitchService().switch(
    config=config,
    config_path=manifest,
    workspace_root=sync,
    session_root=session,
    definition_root=session,
    project_name="missing",
    include_pack=False,
    include_prompt=False,
    include_objective=False,
  )
  assert result.ok is False
  assert result.error == "project_not_found"


def test_switch_exports_agent_mode_and_hermes_tag(tmp_path: Path) -> None:
  manifest, sync, session = _write_workspace(tmp_path)
  config = MetagitConfigManager(manifest).load_config()
  assert not isinstance(config, Exception)
  result = ContextSwitchService().switch(
    config=config,
    config_path=manifest,
    workspace_root=sync,
    session_root=session,
    definition_root=session,
    project_name="attune",
    include_pack=False,
    include_prompt=False,
    include_objective=False,
  )
  assert result.ok is True
  assert result.env.get("METAGIT_AGENT_MODE") == "true"
  assert result.env.get("METAGIT_PROJECT") == "attune"
  assert result.env.get("METAGIT_HERMES_PROFILE") == "attune"
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `uv run pytest tests/core/context/test_context_switch_service.py -v`

- [ ] **Step 3: Implement model + service**

Add `ContextSwitchResult` to `models.py`.

Implement `context_switch_service.py` following `SessionBeginService` structure: construct dependencies in `__init__`, `switch()` validates via `find_project` / `find_repo`, calls `ProjectContextService.switch`, optionally pack/prompt/objective, merges env, returns result. On `ProjectContextBundle.ok is False`, map to `ContextSwitchResult(ok=False, error=bundle.error, ...)`.

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/context/models.py src/metagit/core/context/context_switch_service.py tests/core/context/test_context_switch_service.py
git commit -m "$(cat <<'EOF'
feat: add ContextSwitchService composing pack prompt and objective

EOF
)"
```

---

### Task 3: CLI `metagit context switch`

**Files:**
- Modify: `src/metagit/cli/commands/context.py`
- Test: add cases to `tests/cli/commands/test_context.py` (or new `test_context_switch_cli.py`)

**Interfaces:**
- Consumes: `_context_paths`, `ContextSwitchService.switch`
- Produces: Click command `switch` under `context` group

Shell formatting helper (can live in the service or a small private function in `context.py`):

```python
import shlex

def format_shell_exports(env: dict[str, str]) -> str:
  lines = [f"export {key}={shlex.quote(value)}" for key, value in sorted(env.items())]
  return "\n".join(lines) + ("\n" if lines else "")
```

CLI behavior:
- Positional `project` required; optional `repo`.
- Flags per design (`--tier` default 2, `--no-pack`, `--no-prompt`, `--no-objective`, `--prompt-kind`, `--json`, `-c`).
- On `result.ok is False`: `ClickException` / exit 1.
- If `--json`: `click.echo(result.model_dump_json())` (or `emit_json`).
- Else: `click.echo(format_shell_exports(result.env), nl=False)`; write pack JSON + prompt to stderr via `click.echo(..., err=True)`.

- [ ] **Step 1: Write failing CLI tests**

```python
def test_context_switch_json_ok(tmp_path, monkeypatch):
  # fixture similar to service test; invoke:
  # metagit --config app.yaml context switch attune --json --no-pack --no-prompt --no-objective -c manifest
  # assert exit 0, JSON has ok true and env.METAGIT_PROJECT


def test_context_switch_default_stdout_is_exports_only(tmp_path, monkeypatch):
  # invoke without --json with opt-outs
  # assert stdout lines all startswith "export "
  # assert "METAGIT_AGENT_MODE" in stdout
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement command** near other `context` commands (after `session begin` is a good place):

```python
@context.command("switch")
@click.argument("project")
@click.argument("repo", required=False, default=None)
@click.option("--definition", "-c", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--tier", type=click.IntRange(0, 2), default=2, show_default=True)
@click.option("--no-pack", is_flag=True, default=False)
@click.option("--no-prompt", is_flag=True, default=False)
@click.option("--no-objective", is_flag=True, default=False)
@click.option(
  "--prompt-kind",
  type=click.Choice(["context-switch", "session-start"]),
  default="context-switch",
  show_default=True,
)
@click.option("--json", "as_json", is_flag=True, default=False)
@click.pass_context
def switch_cmd(...):
  ...
```

Use `shell_complete=complete_projects` / `complete_repos` on arguments if Click version in repo supports it on arguments; otherwise document completion via options only — prefer matching existing positional style in this codebase (check `project` commands). If arguments cannot complete, add optional `--project`/`--repo` aliases only if needed for completion — **stick to positionals as designed**.

- [ ] **Step 4: Run CLI tests — PASS**

- [ ] **Step 5: Commit**

```bash
git add src/metagit/cli/commands/context.py tests/cli/commands/test_context_switch_cli.py
git commit -m "$(cat <<'EOF'
feat: add metagit context switch CLI bootstrap command

EOF
)"
```

---

### Task 4: MCP `metagit_context_switch`

**Files:**
- Modify: `src/metagit/core/mcp/tool_registry.py` — add `"metagit_context_switch"` to `_active_tools` near other context tools
- Modify: `src/metagit/core/mcp/runtime.py` — schema + `_dispatch_tool` branch
- Test: `tests/core/mcp/test_runtime.py`

**Interfaces:**
- Schema args: `project_name` (required), `repo_name`, `tier` (default 2), `include_pack`, `include_prompt`, `include_objective`, `prompt_kind`
- Dispatch: resolve roots like `metagit_session_begin` / pack tools; call `ContextSwitchService().switch(...)`; return `model_dump(mode="json")`
- Keep `metagit_project_context_switch` dispatch untouched

- [ ] **Step 1: Write failing runtime test** asserting tool is listed and a call with fixture workspace returns `ok` + `env`

Mirror `test_tools_call_project_context_switch_*` patterns in the same file.

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Register + implement dispatch**

Schema:

```python
"metagit_context_switch": {
  "type": "object",
  "required": ["project_name"],
  "properties": {
    "project_name": {"type": "string"},
    "repo_name": {"type": "string"},
    "tier": {"type": "integer", "enum": [0, 1, 2]},
    "include_pack": {"type": "boolean"},
    "include_prompt": {"type": "boolean"},
    "include_objective": {"type": "boolean"},
    "prompt_kind": {"type": "string", "enum": ["context-switch", "session-start"]},
  },
  "additionalProperties": False,
},
```

- [ ] **Step 4: Run MCP tests — PASS**

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/mcp/tool_registry.py src/metagit/core/mcp/runtime.py tests/core/mcp/test_runtime.py
git commit -m "$(cat <<'EOF'
feat: add MCP metagit_context_switch tool

EOF
)"
```

---

### Task 5: Docs, skills, modality, changelog, router

**Files:**
- Create: `docs/reference/context-switch.md` with `<!-- modality:context_switch -->`, CLI/MCP/prompt usage, tag table (`hermes_profile`, `working_dir`, `default_task_namespace`)
- Modify: `mkdocs.yml` nav to include the page
- Modify: `docs/agents.md` — one row/link for context switch + modality anchor
- Modify: `skills/metagit-context-pack/SKILL.md` and `skills/metagit-workspace-scope/SKILL.md` — document `metagit context switch` as preferred mid-session entry; keep MCP lean tool as alternative
- Run: `task skills:sync` (or project’s skills sync task) so `src/metagit/data/skills/` mirrors
- Modify: `scripts/modality-parity.yml` — add `context_switch` feature with cli/mcp/documentation/skills markers
- Run: `task generate:modality-registry` if that is the project convention after YAML edits
- Modify: `CHANGELOG.md` Unreleased Added
- Modify: `.mex/ROUTER.md` Working bullet
- Optionally extend `.mex/patterns/mcp-project-context.md` with CLI/orchestrator pointer

- [ ] **Step 1: Write docs + skill updates + modality entry**

Modality YAML sketch:

```yaml
  - id: context_switch
    description: Full agent context switch with pack, prompt, objective, and env exports
    service: metagit.core.context.context_switch_service.ContextSwitchService
    reference_doc: docs/reference/context-switch.md
    surfaces:
      cli:
        markers:
          - path: src/metagit/cli/commands/context.py
            contains: '@context.command("switch")'
      mcp:
        markers:
          - path: src/metagit/core/mcp/tool_registry.py
            contains: metagit_context_switch
          - path: src/metagit/core/mcp/runtime.py
            contains: metagit_context_switch
      documentation:
        markers:
          - path: docs/reference/context-switch.md
            contains: "modality:context_switch"
          - path: docs/agents.md
            contains: "modality:context_switch"
      skills:
        markers:
          - path: src/metagit/data/skills/metagit-context-pack/SKILL.md
            contains: "modality:context_switch"
          - path: src/metagit/data/skills/metagit-workspace-scope/SKILL.md
            contains: "modality:context_switch"
```

- [ ] **Step 2: Sync skills + generate modality registry**

Run: `task skills:sync` and `task generate:modality-registry` (use Taskfile names present in repo).

- [ ] **Step 3: QA gate**

Run: `task qa:prepush` until green.

- [ ] **Step 4: GitNexus**

Run: `task gitnexus:analyze`

- [ ] **Step 5: Commit**

```bash
git add docs/reference/context-switch.md docs/agents.md mkdocs.yml skills/ src/metagit/data/skills/ scripts/modality-parity.yml CHANGELOG.md .mex/ROUTER.md
git commit -m "$(cat <<'EOF'
docs: document context switch CLI MCP prompt and tag conventions

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Compose `ProjectContextService.switch` | Task 2 |
| Default tier-2 + prompt + objective + opt-outs | Tasks 2–3 |
| Keep existing env keys + `METAGIT_AGENT_MODE` | Task 2 |
| Tag-derived env exports | Task 2 + Task 5 docs |
| Prompt kind `context-switch` + keep `session-start` | Task 1 |
| CLI `context switch` + shell-eval / `--json` | Task 3 |
| MCP `metagit_context_switch` | Task 4 |
| Lean MCP unchanged | Task 4 |
| Skills + modality + tag docs | Task 5 |
| Independent of `nav` | All tasks |

## Self-review notes (plan author)

- No TBDs left for objective hard-fail (hard fail when included).
- Session vs sync root wiring must match existing MCP/session begin — implementer verifies against `_context_paths` and `metagit_project_context_switch` dispatch before coding Task 2.
- PromptKind Literal check uses `typing.get_args`.
