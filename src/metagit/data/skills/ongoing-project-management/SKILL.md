---
name: ongoing-project-management
description: Ongoing workspace and project management for OpenClaw and Hermes agents. Use when starting work, organizing repos, or before creating a new project folder so existing metagit projects are reused instead of duplicated.
---

# Ongoing Project Management

Use this skill when the user starts new work, reorganizes repositories, or asks you to create a project folder. Metagit is the source of truth for what already exists in the workspace.

## Concepts

Metagit uses a three-level hierarchy (see project terminology docs):

| Level | Meaning |
|-------|---------|
| **Workspace** | Root folder where projects are synced (from app config `workspace.path`, often `./.metagit/`). Holds many projects. |
| **Project** | Named group of one or more Git repositories. Multi-repo products are one project; unrelated repos can also share a workspace under different project names. |
| **Repo** | A single Git repository entry under `workspace.projects[].repos` in `.metagit.yml`. |

A **project** is not always “one product.” It is whatever grouping helps the user and agents reason about related (or intentionally grouped) repositories. A workspace may contain unrelated projects side by side (for example `default`, `client-a`, `experiments`).

The umbrella `.metagit.yml` (workspace definition, often `kind: umbrella`) lives in a coordinating repository or central config checkout. Application repos may have their own `.metagit.yml` for metadata mode.

## Mandatory: check before creating folders

**Never** create a new project directory or clone into the workspace until you have checked metagit for an existing match.

1. **Locate the workspace definition**
   - Prefer the user’s umbrella `.metagit.yml` if known.
   - Otherwise use `.metagit.yml` in the current repo with `--definition /path/to/.metagit.yml`.

2. **List configured projects and repo counts**
   ```bash
   metagit config info --config-path /path/to/.metagit.yml
   metagit project list --config /path/to/.metagit.yml --project default
   ```
   Repeat `--project` for each project name returned by `config info`.

3. **Search managed repos by name, URL fragment, or tag**
   ```bash
   metagit search "<proposed-name-or-url>" --definition /path/to/.metagit.yml
   metagit search "<name>" --definition /path/to/.metagit.yml --json
   ```

4. **Inspect on disk** (workspace path from app config, default `./.metagit/`)
   - Expected layout: `{workspace.path}/{project_name}/{repo_name}/`
   - If the directory already exists, **reuse it**; do not create a parallel tree.

5. **Decide**
   - **Match found** → use existing project/repo; run `metagit project sync` only if the user wants checkouts refreshed.
   - **No match** → proceed with registration steps below (still add to workspace; do not leave orphan folders).

## Registering new work in the workspace

### New repository in an existing project

From the directory containing the workspace `.metagit.yml` (or pass `--config`):

```bash
metagit project repo add --project <project_name> --prompt
# or non-interactive:
metagit project repo add --project <project_name> --name <repo> --url <git-url>
metagit config validate --config-path .metagit.yml
metagit project sync --project <project_name>
```

In the new application repo (if applicable):

```bash
cd /path/to/new/repo
metagit init
metagit detect repo --force   # optional: enrich .metagit.yml
```

### New project group (new `workspace.projects[]` entry)

There is no separate `project create` CLI today. Add a project block to `.metagit.yml`:

```yaml
workspace:
  projects:
    - name: my-new-project
      description: Short purpose for agents and humans
      repos: []
```

Then validate, add repos, and sync:

```bash
metagit config validate --config-path .metagit.yml
metagit project repo add --project my-new-project --prompt
metagit project sync --project my-new-project
```

Choose a **distinct project name**; avoid duplicating an existing `workspace.projects[].name`.

### New umbrella workspace

When bootstrapping a workspace coordinator repo:

```bash
metagit init --kind umbrella
metagit project repo add --project default --prompt
metagit project sync
```

## Ongoing session habits

At the start of sustained work:

1. Run **discovering-workspace-scope** (or `metagit mcp serve --status-once` when MCP is available).
2. Confirm **active project** matches the user’s intent (`metagit workspace select --project <name>` when switching).
3. Use **`metagit search`** before assuming a repo is missing or lives elsewhere.
4. For multi-repo tasks, prefer **metagit-control-center** or **coordinating-multi-repo-implementation** over ad-hoc cloning.

When the user names a target folder:

- Resolve it against managed config first.
- If unmanaged but present on disk under the project sync folder, report it and offer to add via `metagit project repo add` rather than recreating.

## OpenClaw and Hermes setup

Install bundled skills (including this one) for agent hosts:

```bash
metagit skills list
metagit skills install --scope user --target openclaw --target hermes
metagit mcp install --scope user --target openclaw --target hermes
```

Use `--scope project` when installing into a specific umbrella repository checkout.

## Output contract

After project-management actions, report:

- workspace definition path used
- whether the target was **existing** or **newly registered**
- project name and repo name(s) affected
- sync status if `project sync` was run
- recommended next command (`workspace select`, `project select`, or `detect`)

## Safety

- Do not clone, delete, or overwrite sync directories without explicit user approval.
- Do not edit `.metagit.yml` without validating afterward (`metagit config validate`).
- Prefer reusing configured repos over creating duplicate checkouts.
- Keep unrelated experiments in separate `workspace.projects` entries when the user wants clear boundaries.
