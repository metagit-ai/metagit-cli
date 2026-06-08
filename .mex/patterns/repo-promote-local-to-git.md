---
name: repo-promote-local-to-git
description: Migrate a path-based workspace repo entry to a git-managed clone under the sync folder.
edges:
  - target: patterns/add-managed-repo-search.md
    condition: before promoting, confirm the repo name and project via managed search
last_updated: 2026-06-07
---

# Repo promote (local path → git-managed clone)

## When to use

A workspace repo is registered with `path:` (symlink mount to a user folder) and you want a **git clone under `{workspace.path}/{project}/{repo}/`** with the manifest entry using `url:` only.

## Steps

1. **Confirm entry** — `metagit search "<repo>" -c .metagit.yml --json` and `metagit workspace repo list --project <p> --json`.
2. **Dry-run** — `metagit project repo promote --name <repo> --dry-run --json` (add `--url` if origin is missing).
3. **Apply** — `metagit project repo promote --name <repo> --json` (use `--force` when `protected: true`).
4. **Validate** — `metagit config validate -c .metagit.yml` and confirm mount is a directory clone, not a symlink.

## Behavior

- Resolves URL from `--url`, manifest `url`, or git `origin` on the source path.
- Removes the project sync mount (symlink or directory) without deleting the original source folder.
- Clears `path`, sets `url`, saves `.metagit.yml`, runs `project sync`.
- Mount path must not be resolved through existing symlinks (see `RepoPromoteService`).

## Verify

- `uv run pytest tests/core/project/test_repo_promote_service.py tests/cli/commands/test_project_repo_promote.py`
