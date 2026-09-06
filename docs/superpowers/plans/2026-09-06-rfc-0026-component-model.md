# RFC-0026 Component Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a first-class Component model, catalog adapter, and `config validate` integration without changing existing `paths` / top-level `components` YAML types.

**Architecture:** New `metagit.core.component` package (models, identity, path normalize, catalog). `ProjectPath.components` is an optional nested list. Validation lives next to graph validation and is invoked from `metagit config validate`. Application `paths[]` map into the catalog at runtime.

**Tech Stack:** Python 3.13, Pydantic v2, Click, pytest, existing JSON schema generator.

## Global Constraints

- Additive and backward compatible; manifests with no `repos[].components` keep today’s behavior.
- `Component` is not a `ProjectPath` subclass; git-only fields are forbidden.
- PathMetadata is a helper module, not a Pydantic parent of `ProjectPath` (preserve YAML key order).
- Identity is always `project/repo/component`; application manifests use `config.name` for both.
- No `metagit component` CLI, MCP tools, graph endpoint field, or compile flags in this slice.
- 2-space indent; `#/usr/bin/env python` on new files; `T | Exception` / `str | ValueError` unions for helpers.
- Do not commit unless the user asks.

---

## File map

**Create**

- `src/metagit/core/project/path_metadata.py`
- `src/metagit/core/component/__init__.py`
- `src/metagit/core/component/models.py`
- `src/metagit/core/component/identity.py`
- `src/metagit/core/component/paths.py`
- `src/metagit/core/component/catalog.py`
- `src/metagit/core/config/component_validation.py`
- `tests/core/component/test_identity.py`
- `tests/core/component/test_paths.py`
- `tests/core/component/test_models.py`
- `tests/core/component/test_catalog.py`
- `tests/core/config/test_component_validation.py`
- `tests/cli/commands/test_config_validate_components.py`
- `tests/fixtures/components/` (YAML fixtures)
- `docs/concepts/components.md`

**Modify**

- `src/metagit/core/project/models.py` — optional `components` list
- `src/metagit/core/workspace/agent_profile_models.py` — optional `component` on issues
- `src/metagit/core/agent/profile_service.py` — validate catalog profiles
- `src/metagit/cli/commands/config.py` — call `validate_components`
- `src/metagit/core/config/schema_generator.py` — `agent_prompt` on Component
- `scripts/modality-parity.yml` — `component_model`
- `docs/agents.md`, `llms.txt`, `docs/reference/metagit-config.md`, `mkdocs.yml`, `CHANGELOG.md`
- `.mex/ROUTER.md`, `.mex/patterns/INDEX.md`, `.mex/patterns/component-model.md`

---

### Task 1: Identity and path helpers

**Files:** `identity.py`, `paths.py`, tests

- [x] Spec locked: `component_id` / `parse_component_id` / `normalize_repo_relative_path`
- [ ] Failing tests then implementation (TDD)

### Task 2: Component models + ProjectPath.components

**Files:** `models.py`, `path_metadata.py`, `project/models.py`

- [ ] Minimal/full/forbid-git-fields/command coerce tests
- [ ] `ProjectPath.components` default empty; existing ProjectPath tests still pass

### Task 3: Catalog

**Files:** `catalog.py`

- [ ] Native nested, paths adapter, ref-only skipped, empty repo, application identity

### Task 4: Validation + config validate + agent_profile

**Files:** `component_validation.py`, `profile_service.py`, CLI hook

- [ ] Duplicate name/path, escape, unknown local dep, cycle, missing dir iff cloned, nested allowed
- [ ] CLI abort on planted error; clean no-components fixture still succeeds

### Task 5: Schema, docs, GROW, QA

- [ ] `task generate:schema` (or `task skills:sync generate:schema`)
- [ ] Public docs + changelog + modality + ROUTER
- [ ] `task qa:prepush` then `task gitnexus:analyze`

---

## Interfaces (consumed by later tasks)

```python
def component_id(project: str, repo: str, component: str) -> str: ...
def parse_component_id(value: str) -> ComponentId | ValueError: ...
def normalize_repo_relative_path(raw: str) -> str | ValueError: ...
def path_metadata_kwargs(source: object) -> dict[str, object]: ...

class ComponentCatalog:
  def list(self, config: MetagitConfig) -> list[ResolvedComponent]: ...

def validate_components(config: MetagitConfig, *, definition_root: str | Path) -> list[str]: ...
```

`ResolvedComponent.source` ∈ `{"native", "path", "legacy_component"}`.
