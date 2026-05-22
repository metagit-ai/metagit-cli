---
name: context-pack-repo-cards
description: Building tier-1 context pack repo cards (RepoCardService) from index + git inspect + manifest rows.
triggers:
  - "RepoCardService"
  - "repo card"
  - "context pack tier 1"
edges:
  - target: context/conventions.md
    condition: when editing Python/services under src/metagit/core
last_updated: 2026-05-21
---

# Context pack tier-1 repo cards

## Goal

Produce `RepoCardResult` payloads for MCP/CLI tier-1 context packs: combine `WorkspaceIndexService.build_index` rows with `inspect_repo_state`, manifest URLs/descriptions/tags, stack root file hints, and composed agent instructions.

## Steps

1. **Locate the row**: Use `WorkspaceIndexService().build_index(config, workspace_root)` and pick `project_name` + `repo_name`. `build_one` raises `ValueError` when unknown.
2. **Manifest row**: Resolve `WorkspaceProject` and `ProjectPath` from `config.workspace` for tags (string list `key=value`), `description`, `url`, and layered instructions.
3. **Git inspect**: Call `inspect_repo_state(repo_path)` only when `exists` and `is_git_repo` from the index row; otherwise use empty inspect dict and zeros.
4. **Agent excerpt**: Use `AgentInstructionsResolver().resolve(config, project=..., repo=...).effective` truncated to **500 chars**; if blank, fall back to repo then project manifest `agent_instructions` (same cap).
5. **Stack hints**: Check fixed root filenames (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `Dockerfile`, `Taskfile.yml`, `Makefile`, `README.md`) with `Path(os.path.join(root, name)).is_file()` only when clone exists on disk.
6. **Health flags** (deterministic order): `missing_clone` (`exists` False); `dirty` (`inspect["dirty"]` True); `behind_remote` (`behind` int > 0); `stale_head_30d` (`head_commit_age_days` > 30).

## Verify

- `uv run pytest tests/core/context/test_repo_card_service.py -q`
