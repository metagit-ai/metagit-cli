---
name: agent
description: "Skill for the Agent area of metagit-cli. 122 symbols across 17 files."
metadata:
  internal: true
---
# Agent

122 symbols | 17 files | Cohesion: 74%

## When to Use

- Working with code in `src/`
- Understanding how test_init_overlay_committed_default_path, test_init_overlay_local_path, test_local_overlay_overrides_committed_manifest work
- Modifying agent-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/agent/registry.py` | load_bundled_manifest, template_dir, _load_bundled_manifest, _bundled_template_dir, resolve_source (+15) |
| `src/metagit/core/agent/overlay.py` | overlay_template_dir, resolve_template_source, overlay_relative_for_scope, overlay_path_for_template, ensure_overlay_root (+14) |
| `src/metagit/core/agent/service.py` | init_overlay, template_detail, create, __post_init__, render_template (+10) |
| `src/metagit/core/agent/dispatch.py` | _build_install, _install_command, build_plan, _validate_scope_inputs, _resolve_project_repo (+7) |
| `tests/core/agent/test_agent_service.py` | test_create_writes_claude_code_agent, test_create_refuses_overwrite_without_force, test_create_hermes_installs_skill, test_create_opencode_uses_subagent_frontmatter, test_create_cursor_agent (+6) |
| `tests/core/agent/test_agent_overlay.py` | _normalize_path_text, _write_manifest_root, test_init_overlay_committed_default_path, test_init_overlay_local_path, test_local_overlay_overrides_committed_manifest (+3) |
| `tests/core/agent/test_agent_dispatch.py` | _workspace_manifest, test_dispatch_plan_repo_implementer_handoff, test_dispatch_plan_detects_installed_artifact, test_dispatch_plan_requires_repo_scope_inputs, test_dispatch_plan_cli_json (+2) |
| `src/metagit/cli/commands/agent.py` | agent_show, _require_manifest_root, agent_dispatch_plan, agent_overlay_path, agent_schema |
| `src/metagit/core/agent/paths.py` | expand_agent_path, autodetect_agent_targets, resolve_skills_directory, resolve_agents_directory, resolve_vendor_artifact_path |
| `src/metagit/core/init/prompts.py` | load_answers_file, build_builtin_defaults, resolve_prompt_default, collect_answers |

## Entry Points

Start here when exploring this area:

- **`test_init_overlay_committed_default_path`** (Function) — `tests/core/agent/test_agent_overlay.py:33`
- **`test_init_overlay_local_path`** (Function) — `tests/core/agent/test_agent_overlay.py:55`
- **`test_local_overlay_overrides_committed_manifest`** (Function) — `tests/core/agent/test_agent_overlay.py:75`
- **`test_init_overlay_refuses_without_force`** (Function) — `tests/core/agent/test_agent_overlay.py:114`
- **`test_cli_overlay_init_committed`** (Function) — `tests/core/agent/test_agent_overlay.py:131`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `AgentTemplateRenderer` | Class | `src/metagit/core/agent/renderer.py` | 16 |
| `InitTemplateRenderer` | Class | `src/metagit/core/init/renderer.py` | 44 |
| `test_init_overlay_committed_default_path` | Function | `tests/core/agent/test_agent_overlay.py` | 33 |
| `test_init_overlay_local_path` | Function | `tests/core/agent/test_agent_overlay.py` | 55 |
| `test_local_overlay_overrides_committed_manifest` | Function | `tests/core/agent/test_agent_overlay.py` | 75 |
| `test_init_overlay_refuses_without_force` | Function | `tests/core/agent/test_agent_overlay.py` | 114 |
| `test_cli_overlay_init_committed` | Function | `tests/core/agent/test_agent_overlay.py` | 131 |
| `test_service_init_overlay_merged_source` | Function | `tests/core/agent/test_agent_overlay.py` | 160 |
| `agent_show` | Function | `src/metagit/cli/commands/agent.py` | 95 |
| `overlay_template_dir` | Function | `src/metagit/core/agent/overlay.py` | 231 |
| `resolve_template_source` | Function | `src/metagit/core/agent/overlay.py` | 316 |
| `test_overlay_merge` | Function | `tests/core/agent/test_agent_catalog.py` | 53 |
| `agent_dispatch_plan` | Function | `src/metagit/cli/commands/agent.py` | 279 |
| `agent_overlay_path` | Function | `src/metagit/cli/commands/agent.py` | 581 |
| `overlay_relative_for_scope` | Function | `src/metagit/core/agent/overlay.py` | 39 |
| `overlay_path_for_template` | Function | `src/metagit/core/agent/overlay.py` | 48 |
| `ensure_overlay_root` | Function | `src/metagit/core/agent/overlay.py` | 82 |
| `overlay_has_files` | Function | `src/metagit/core/agent/overlay.py` | 93 |
| `init_overlay_from_bundled` | Function | `src/metagit/core/agent/overlay.py` | 146 |
| `test_create_writes_claude_code_agent` | Function | `tests/core/agent/test_agent_service.py` | 45 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Agent_list → Overlay_template_dir` | cross_community | 8 |
| `Agent_list → _bundled_template_dir` | cross_community | 7 |
| `Agent_list → _deep_merge_dict` | cross_community | 7 |
| `Agent_export → _bundled_template_dir` | cross_community | 7 |
| `Agent_export → _deep_merge_dict` | cross_community | 7 |
| `Agent_show → Overlay_template_dir` | cross_community | 7 |
| `Agent_validate → Overlay_template_dir` | cross_community | 7 |
| `Agent_dispatch_plan → Expand_agent_path` | cross_community | 7 |
| `Agent_create → _validate_merged_payload` | cross_community | 6 |
| `Agent_create → _bundled_template_dir` | cross_community | 6 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 4 calls |
| Mcp | 2 calls |
| Web | 2 calls |
| Skills | 2 calls |
| Init | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_init_overlay_committed_default_path"})` — see callers and callees
2. `gitnexus_query({query: "agent"})` — find related execution flows
3. Read key files listed above for implementation details
