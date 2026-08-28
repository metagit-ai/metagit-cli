# RFC-0024: Plugin / Detector / Skill Extension Points — Design

**Status:** Proposed  
**Date:** 2026-08-27  
**Series:** [Agent Reliability series index](2026-08-27-agent-reliability-series-index.md)  
**Depends on:** Existing provider plugin registry (`metagit.core.providers`), skills packaging (`metagit skills`), context pack service, shipped detection/stack hints, RFC-0018 ontology adapters (pattern reference)  
**Plan:** (pending — `docs/superpowers/plans/2026-08-27-rfc-0024-plugins.md`)  
**Related:** [Context packs](2026-05-21-context-packs-design.md) · [RFC-0018 pluggable ontology](2026-07-31-rfc-0018-pluggable-ontology-layer-design.md) · `docs/repository_detection.md`

## Summary

Metagit already ships **git provider plugins** and bundled skills, but third parties cannot extend **repo detectors**, **context-pack contributors**, or **skill discovery** without forking core. **RFC-0024 defines stable Protocol-based extension points**, optional **`importlib.metadata` entry-point discovery**, and CLI **`metagit plugins list|describe`**. v1 includes one **reference external package** under `examples/metagit-plugin-demo/` demonstrating a custom stack detector and context-pack fragment contributor. Extensions run **in-process** with explicit enable lists — no arbitrary code execution from manifest alone.

## Goals

1. **`ExtensionRegistry`** — central registry for plugins by kind: `detector`, `context_contributor`, `skill_pack`, `provider` (wrap existing provider registry).
2. **Protocol definitions** — typed interfaces in `metagit.core.plugins.protocols` using `typing.Protocol` + pydantic result DTOs.
3. **Entry-point discovery** — optional load via `[project.entry-points."metagit.plugins"]` in installed packages; disabled unless listed in config allowlist.
4. **Built-in adapters unchanged** — core detectors remain default; plugins augment, never replace security boundaries.
5. **CLI `metagit plugins list|describe|doctor`** — JSON inventory of loaded plugins, versions, enabled state, import errors.
6. **Context pack hook** — contributors return bounded `ContextFragment` records merged into tier-1 cards or tier-2 slices with token budget.
7. **Detector hook** — plugins return extra `stack_hints` / `health_flags` given repo path + manifest row.
8. **Example package** — `examples/metagit-plugin-demo/` installable via `uv pip install -e` with one detector + one contributor.
9. **Parity** — MCP `metagit_plugins_list`, skill `metagit-cli`, docs `docs/reference/plugins.md`, modality registry.

## Non-Goals

- Arbitrary CLI subcommand injection from plugins (core commands stay in metagit-cli).
- Remote plugin marketplace or unsigned wheel install flows.
- Sandboxed subprocess isolation for plugins in v1 (trust allowlist model).
- Replacing bundled skills catalog or MCP server plugin architecture.
- Policy engine plugins (RFC-0022) — may share registry in v1.1.
- Federation cross-workspace plugin sync (RFC-0023).

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | Plugins are **opt-in via allowlist** in `.metagit.yml` or appconfig — discovery alone does not enable. |
| D2 | **In-process only** — same trust model as git provider plugins today. |
| D3 | Protocols use **`typing.Protocol`** + pydantic result models; no ABC inheritance required for third parties. |
| D4 | Entry-point group name: **`metagit.plugins`** with ephem format `kind:name = module:attr`. |
| D5 | Contributors MUST declare **`max_tokens`** budget; pack service truncates with `truncated: true`. |
| D6 | Plugin load failures are **non-fatal** — doctor/list reports error per plugin; core commands continue. |
| D7 | Detectors MUST NOT perform network I/O in v1 — filesystem + manifest only (document in protocol docstring). |
| D8 | Bundled `examples/metagit-plugin-demo` is the conformance test — CI imports it in integration job. |

## Architecture

```text
metagit plugins list|describe|doctor
              │
              ▼
      ExtensionRegistry
        ├─► Builtin providers (existing)
        ├─► EntryPointLoader (importlib.metadata)
        └─► Config allowlist filter
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 Detector  ContextContrib  SkillPack
 plugins   plugins         plugins
    │         │               │
    ▼         ▼               ▼
RepoCard   ContextPack    skills install
Service    Service        (manifest refs)
```

**Package placement (proposed):**

| Module | Role |
|--------|------|
| `src/metagit/core/plugins/protocols.py` | `DetectorPlugin`, `ContextContributorPlugin`, `SkillPackPlugin` Protocols |
| `src/metagit/core/plugins/models.py` | `PluginInfo`, `ContextFragment`, `DetectorResult` |
| `src/metagit/core/plugins/registry.py` | `ExtensionRegistry` |
| `src/metagit/core/plugins/loader.py` | Entry-point + allowlist loading |
| `src/metagit/core/plugins/doctor.py` | Import/contract validation |
| `src/metagit/cli/commands/plugins.py` | list, describe, doctor |

## Protocol sketches

### DetectorPlugin

```python
class DetectorPlugin(Protocol):
    id: str
    version: str

    def describe(self) -> dict[str, Any]: ...

    def detect(
        self,
        repo_path: str,
        *,
        project_name: str,
        repo_name: str,
        manifest_tags: dict[str, str],
    ) -> DetectorResult | Exception: ...


class DetectorResult(BaseModel):
    stack_hints: list[str] = Field(default_factory=list)
    health_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
```

### ContextContributorPlugin

```python
class ContextContributorPlugin(Protocol):
    id: str
    version: str

    def contribute(
        self,
        *,
        tier: Literal[1, 2],
        project_name: str | None,
        repo_name: str | None,
        repo_path: str | None,
        max_tokens: int,
    ) -> ContextFragment | Exception: ...


class ContextFragment(BaseModel):
    plugin_id: str
    title: str
    body: str
    token_estimate: int
    truncated: bool = False
    repo_scoped: bool = True
```

Merge order: core card fields → enabled contributors sorted by `priority` config (default 100).

### SkillPackPlugin

Advertises additional skill directories for `metagit skills install`:

```python
class SkillPackPlugin(Protocol):
    id: str
    def skill_paths(self) -> list[str]: ...  # absolute or package-relative
```

## Configuration

```yaml
plugins:
  enabled:
    - detector:demo-node
    - context:demo-readme-excerpt
  settings:
    detector:demo-node:
      flag_threshold: 3
```

Env: `METAGIT_PLUGINS_ENABLED=detector:demo-node,context:demo-readme-excerpt` (comma-separated, merges with file).

Entry-point registration (external package `pyproject.toml`):

```toml
[project.entry-points."metagit.plugins"]
"detector:demo-node" = "metagit_plugin_demo.detectors:node_detector"
"context:demo-readme-excerpt" = "metagit_plugin_demo.context:readme_contributor"
```

## Interfaces

### CLI

```bash
metagit plugins list [--json]
metagit plugins describe PLUGIN_ID [--json]
metagit plugins doctor [--json]
```

**`plugins list` JSON row:**

```json
{
  "id": "detector:demo-node",
  "kind": "detector",
  "version": "0.1.0",
  "enabled": true,
  "source": "entrypoint",
  "module": "metagit_plugin_demo.detectors",
  "error": null
}
```

### MCP (ACTIVE-gated)

| Tool | Purpose |
|------|---------|
| `metagit_plugins_list` | Enabled + discovered inventory |
| `metagit_plugins_doctor` | Load/contract diagnostics |

Context pack MCP gains optional `include_plugins: true` (default false) to attach fragments.

### Integration points

| Call site | Behavior |
|-----------|----------|
| `RepoCardService.build_card` | After filesystem stack hints, merge detector plugin results (dedupe hints) |
| `ContextPackService.build_pack` | When `include_plugins` or config default, append fragments within tier token ceiling |
| `metagit skills install` | Union bundled + skill pack plugin paths when `--all-plugins` (v1.1) |

## Example package layout

```text
examples/metagit-plugin-demo/
├── pyproject.toml          # entry-points + dev dependency on metagit-cli
├── README.md
└── metagit_plugin_demo/
    ├── detectors.py        # flags package.json + pnpm-lock.yaml
    └── context.py          # README excerpt contributor
```

README documents: `uv pip install -e examples/metagit-plugin-demo`, enable in `.metagit.yml`, run `metagit plugins doctor`, `metagit context pack --tier 1 --include-plugins --json`.

## Persistence

None new. Plugin config lives in manifest/appconfig; no plugin state files in v1.

## Acceptance

- `metagit plugins list --json` shows built-in provider plugins + demo plugin when installed and enabled.
- Disabled plugin in config does not load even if entry-point present.
- Demo detector adds `stack_hints` containing `pnpm` on fixture repo with `pnpm-lock.yaml`.
- Demo context contributor appends fragment to tier-1 pack under token budget; sets `truncated` when budget exceeded.
- Load error in one plugin does not break `context pack` — doctor reports error.
- MCP list/doctor parity.
- Modality `plugins_registry`; docs reference; example package CI import test.
- No new runtime deps beyond stdlib `importlib.metadata`.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| Context pack / repo card services | Hook surfaces |
| Provider registry pattern | Loader model precedent |
| RFC-0018 ontology adapters | Similar adapter registry pattern |
| RFC-0022 policy (future) | Optional policy plugin kind |

## Suggested PR split

1. **Protocols + registry + loader** — no hooks, unit tests with inline fake plugins.
2. **CLI/MCP list/doctor** — discovery and allowlist.
3. **Repo card + context pack hooks** — `--include-plugins`, merge logic.
4. **Example package + docs** — demo install path, plugins.md, modality parity.

## Open questions

1. Namespace entry-points as `metagit.detectors` vs single `metagit.plugins`?  
   **Recommendation:** single group with `kind:id` prefix — simpler doctor UX.
2. Should plugins run in **`METAGIT_AGENT_MODE` only**?  
   **Recommendation:** no — same enable list for humans and agents; doctor validates both paths.
3. Dynamic reload on manifest change?  
   **Recommendation:** no — restart CLI/MCP server to reload (document).
