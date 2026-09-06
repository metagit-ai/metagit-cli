---
name: component-agent-profile
description: Merge agent_profile workspace → project → repo → component (RFC-0029).
triggers:
  - "agent_profile"
  - "effective_profile"
  - "component_name"
  - "RFC-0029"
edges:
  - target: "component-model.md"
    condition: when Component.agent_profile or repos[].components[] shape is involved
  - target: "../context/conventions.md"
    condition: when writing or reviewing profile merge code
last_updated: 2026-09-06
---

# Component agent_profile merge (RFC-0029)

## Context

Design decisions 3–4: `docs/superpowers/specs/2026-09-06-rfc-0029-component-compile-design.md`.
Service: `src/metagit/core/agent/profile_service.py` (`effective_profile`, `_merge_for_repo`, `_merge_profiles`).
Models: `AgentProfileLayer.scope` includes `"component"`; `EffectiveAgentProfile.component_name`.
Tests: `tests/core/agent/test_agent_profile_service.py`.

## Steps

1. `effective_profile(project_name, repo_name, component_name=None)` finds project/repo as today.
2. `component_name is None` → `_merge_for_repo` only (`component_name` stays None). Used by `apply()`.
3. Named component must exist on `repo.components`. Missing name → `None` (no repo-only fallback).
4. Merge workspace → project → repo → component via `_merge_profiles`. `inherit: false` on the component replaces parents.
5. Append `AgentProfileLayer(scope="component", ...)` only when the component has `agent_profile`.

## Gotchas

- Do not silently fall back to repo merge when the component name is unknown.
- Do not add compile CLI/`--component` in the profile-merge slice.
- Use real bundled skill ids in tests (`metagit-cli`, `metagit-workspace-scope`, …).

## Verify

- [ ] `uv run pytest tests/core/agent/test_agent_profile_service.py`
- [ ] Inherit-true appends component skills; inherit-false replaces; unknown name is None
- [ ] `task qa:prepush`

## Update Scaffold

- [ ] `.mex/ROUTER.md` project state
- [ ] This pattern when merge semantics change
