# Imprint, agent map, and sync failure detail

**Status:** Accepted (design)  
**Date:** 2026-09-28  
**Depends on:** Workspace catalog and index, `WorkspaceSyncService`, web sync jobs, `metagit-agent-access` AGENTS.md fences  
**Related:** [Derived projects](../../reference/derived-projects.md) · [RFC-0023 federation](2026-08-27-rfc-0023-federation-design.md) · [Context reduction](2026-09-18-context-reduction-large-workspace-campaigns-design.md) · [Web ops](../../reference/metagit-web.md)

## Problem

Three gaps show up on a top-level umbrella:

1. **Sync failures in the web UI hide the repo that failed.** `WorkspaceSyncService.sync_many` returns per-repo `results` (`project_name`, `repo_name`, `repo_path`, `error`) and a `summary`. When any repo fails, `ok` is false and there is no top-level `error` string. `_run_sync_job` then calls `SyncJobStore.fail` with the fallback `"sync failed"` and drops `summary` and `results`. `SyncDialog` renders that one string. A completed job shows summary counts and ignores `results`. Provider source sync returns `errors[]` (`kind`, `message`) on HTTP 422, and `OpsPanel` shows only `ApiError.message`. `requestJson` looks for a top-level `message`, so the 422 body often becomes the status text.
2. **A weaker model cannot traverse the umbrella without Metagit.** Session prompts tell agents to run `metagit search` and never paste `.metagit.yml`. A model that cannot run the CLI has only the nested manifest. `AGENTS.md` is capped as a short procedure, which is the right size, and it does not point at a flat catalog.
3. **A complex project needs its own umbrella, and the parent still needs that project's repos.** Derived projects copy repos inside one manifest. Federation (proposed) keeps sibling workspaces in a separate read-only catalog. Neither folds one child project into a parent project entry so search, tags, sync, and context packs see `parent-project/repo`.

## Goals

1. Show every failed sync row in the web sync dialog: `project/repo`, checkout path, and that row's `error`. Show every source-sync `errors[]` line as `kind` and `message`.
2. Publish a committed, one-repo-per-line map and a short `AGENTS.md` procedure so a model can find and add repos without running `metagit`.
3. Let one parent project imprint one project from a downstream `.metagit.yml`. Cache that manifest once per source. Resolve repos at read time. Keep the parent file as a pointer plus optional pins.

## Non-goals

- Importing the child manifest's `graph.relationships` into the parent.
- A web UI for imprint pull, push, or agent-map editing.
- Nested identity (`parent/child-project/repo`). Search stays `project/repo`.
- Flattening a whole child workspace into one parent project.
- Write-through of tag edits into the child manifest except `imprint push`.
- Auto-cloning every repo listed in the child project. Pull fetches the child umbrella git repo (the coordinator), not its member repos.
- Replacing RFC-0023 federation.

## Decisions

| # | Decision |
|---|----------|
| D1 | One parent `WorkspaceProject` imprints one child project. Several parent projects may share one source cache via `imprint.id`. |
| D2 | `MetagitConfigManager.load_config` returns the file on disk. An imprint resolver builds the effective project for index, search, context packs, and sync. Save never writes expanded imprint repos back into the parent `.metagit.yml`. |
| D3 | Same repo name: a parent `repos[]` entry replaces the child entry entirely (a pin). `overrides.yml` deep-merges `tags` and replaces `description` only. |
| D4 | Tag and description edits for an imprinted repo go through `imprint override set` into `.metagit/imprints/projects/<parent>/overrides.yml`. `config patch` and Config Studio edit the stored parent manifest only. `imprint push` copies override keys onto the matching child repo and removes the pushed keys from the override file. |
| D5 | The imprint cache lives at the manifest directory: `.metagit/imprints/`. The name `imprints` is always reserved by `reserved_project_names`, because the default sync root is also `./.metagit`. |
| D6 | The agent map is committed at `agent-map/` next to `.metagit.yml`. `.metagit/` stays gitignored, so the map is what a model sees on a fresh clone. |
| D7 | `agent map sync` rewrites an imprinted project's map file only when that imprint resolves. A missing cache leaves the committed file in place and reports `missing_cache`. |
| D8 | A failed sync job stores `summary` and `results`. The dialog lists failed rows open, and skipped rows as a count. Successful rows stay in the summary counts. |
| D9 | A project is either derived or imprinted. `config validate` rejects both on the same project. |
| D10 | Ship order is sync failure detail, then agent map against literal `repos[]`, then imprint. Each slice is usable alone. |

## Slice 1 — Sync failure detail

### Job store

`SyncJobStore.fail` accepts optional `summary` and `results` and stores them on the failed status. `error` remains a short job-level string.

`_run_sync_job`, when `payload["ok"]` is false and `results` is a list:

- Set `error` from `summary` when present: `"{failed} of {total} repos failed"`.
- Persist `summary` and `results`.
- Emit the existing `failed` SSE event and include `summary`.

An exception before `sync_many` returns still fails with `str(exc)` and empty results.

### Sync dialog

On `state === "failed"` or `state === "completed"`:

- Render summary counts when `summary` is present.
- Render each result with `ok === false` and `skipped !== true` as `project_name/repo_name`, `repo_path`, and `error`.
- Render skipped count from `summary.skipped`. A disclosure lists skipped rows (`skipped_reason`) when opened.
- The failure list scrolls inside the dialog. v1 does not page it.

`web/src/api/client.ts` `SyncJobStatus.results` is already typed as a record list. Give the dialog a small typed row (`project_name`, `repo_name`, `repo_path`, `ok`, `skipped`, `skipped_reason`, `error`).

### Source sync panel

On a failed `postSourceSync`, read `ApiError.body`. When `body.errors` is a list, render each `{kind, message}`. Keep `ApiError.message` as the heading when it is more specific than the HTTP status text. `requestJson` should prefer `error.message` when the envelope is `{error: {kind, message}}`, and prefer the first `errors[0].message` when that list exists, so the heading is the server message.

### Tests

- `tests/core/web/test_job_store.py`: `fail` retains summary and results.
- Ops handler test: `sync_many` returning `ok: false` with two failed rows yields a failed job whose `results` length is 2 and whose `error` contains the failed count.
- `web/src/components/SyncDialog.test.tsx`: failed status renders `platform/api` and the row error.
- Ops panel test: 422 body `errors` renders `kind` and `message`.

## Slice 2 — Agent map

### Files

```text
agent-map/projects.txt
agent-map/<project>.txt
```

`projects.txt` columns, tab-separated, after comment lines:

```text
project	repo_count	description	imprint_id
```

`<project>.txt` columns:

```text
repo	url	path	tags	description
```

`tags` is `key=value` pairs joined by `;`. Tabs and newlines in any field become spaces on write. Comment lines start with `#`. The first comment on an imprinted file is the source line (slice 3). A literal project file starts with `# columns: repo url path tags description`.

### AGENTS.md fence

`metagit agent map sync` replaces only the region between `<!-- metagit-agent-map:start -->` and `<!-- metagit-agent-map:end -->`. When the fence is missing, append it. Leave the rest of `AGENTS.md` untouched. When `AGENTS.md` does not exist, create it containing only the fence.

The fence text is a fixed procedure, about forty lines:

- Find a project in `agent-map/projects.txt`, then open `agent-map/<project>.txt`.
- Checkout is the `path` column when set. Otherwise it is `<sync-root>/<project>/<repo>`. `agent map sync` writes the resolved sync root into the fence (app config `workspace.path`, default `./.metagit` relative to the manifest directory).
- To add a repo, paste the stencil as a new `repos[]` item under that project in `.metagit.yml` and append one map line. Do not reorder other keys.
- The stencil is one repo object: `name`, exactly one of `url` or `path`, optional `tags`.

### Command

```bash
metagit agent map sync [-c definition] [--project NAME] [--json]
```

Reads the on-disk manifest (slice 3 switches this to the resolved view). Writes the map files and the fence. `--json` returns `{projects, files_written, warnings}`.

MCP tool `metagit_agent_map_sync` takes optional `project` and returns the same JSON. Active-gated like other catalog tools.

### Docs and modality

Reference: `docs/reference/agent-map.md` with `<!-- modality:agent_map -->`. Register `agent_map` in `scripts/modality-parity.yml` for CLI, MCP, documentation, and the bundled skill note in `metagit-agent-access` (the fence name and the map path). Web surface is out of this slice.

### Tests

- Sync writes `projects.txt` and one repo line from a fixture manifest.
- A second sync replaces the fence once and does not duplicate it.
- A field containing a tab is stored with a space.

## Slice 3 — Imprint

### Schema

On `WorkspaceProject`:

```yaml
imprint:
  id: platform-umbrella       # cache key, shared across parent projects
  project: billing            # project name inside the child manifest
  manifest: .metagit.yml      # path inside the child repo; default .metagit.yml
  url: git@github.com:acme/platform-umbrella.git
  ref: main                   # default main; used with url
  local_path: ../platform-umbrella
```

Exactly one of `url` or `local_path`. `id` and `project` are required. `extra = forbid`.

`config validate` rejects an imprint whose `id` collides with a different url or local_path elsewhere in the same parent manifest. It rejects `derived.enabled` together with `imprint`.

### Cache layout

Under the manifest directory (session/definition root, not the sync root when those differ):

```text
.metagit/imprints/sources/<id>/checkout/    # shallow clone when url is set
.metagit/imprints/sources/<id>/lock.json
.metagit/imprints/projects/<parent>/overrides.yml
```

`lock.json` fields: `id`, `url` or `local_path`, `ref`, `manifest`, `sha`, `fetched_at`. For `local_path`, `sha` is the child repo HEAD when that path is a git checkout, otherwise null.

`overrides.yml`:

```yaml
repos:
  billing-api:
    tags:
      team: payments
    description: Local note
```

Unknown keys in an override repo are ignored. `url` and `path` in the override file do not apply; those changes are parent `repos[]` pins.

`reserved_project_names` always includes `imprints`.

### Pull, status, push

```bash
metagit project imprint pull <parent-project> [--json]
metagit project imprint status <parent-project> [--json]
metagit project imprint push <parent-project> [--json]
metagit project imprint override set <parent-project> --repo NAME [--tag key=value] [--description TEXT] [--json]
metagit project imprint override unset <parent-project> --repo NAME [--tag KEY] [--description] [--json]
```

**Pull (`url`).** Shallow-clone `ref` into `sources/<id>/checkout` with GitPython. When the checkout exists and is clean, fetch and update to `ref`. When it is dirty, fail and leave it untouched. Copy nothing else. Read `<checkout>/<manifest>` and record `sha` in `lock.json`. Then run agent-map sync for that parent project.

**Pull (`local_path`).** Do not clone. Read `<local_path>/<manifest>`, record lock fields, run agent-map sync for that parent project.

**Status.** `state` is `ready`, `missing_cache`, `missing_child_project`, or `unreadable_manifest`. `dirty_checkout` is a separate boolean. Also report `sha`, `fetched_at`, and override repo names. `missing_child_project` means the cache exists and `imprint.project` is not in the child `workspace.projects`. A successful push leaves `state: ready` and `dirty_checkout: true` until the operator commits the cache clone.

**Push.** Apply `overrides.yml` tag keys and descriptions onto the matching repos in the child manifest file, then remove those keys from the override file. For `local_path`, edit that file in place. For `url`, edit `checkout/<manifest>` in the cache clone and leave committing to the operator (`status` reports a dirty checkout afterward). Push does not create a commit or network update. Push fails when the child project or a named override repo is absent.

MCP: `metagit_project_imprint_pull`, `metagit_project_imprint_status`, `metagit_project_imprint_push`, `metagit_project_imprint_override_set`, `metagit_project_imprint_override_unset`. Same arguments as the CLI (`project` required). `override set` requires `repo` and at least one of `tag` or `description`.

### Resolved view

`ImprintResolver.effective_config(config, *, manifest_dir) -> EffectiveConfig` returns a copy used by the workspace index build (and therefore search, context packs, and sync). It does not write the parent manifest.

For each imprinted project:

1. Load the child manifest from the checkout or `local_path`. On failure, keep the parent `repos[]` only and attach warning `missing_cache` or `unreadable_manifest`. Do not drop the project.
2. Select `imprint.project`. On failure, same as above with warning `missing_child_project`.
3. Start from that child project's `repos` (names, urls, paths, tags, components, `ci`, descriptions, agent profiles).
4. Rewrite each child repo path before indexing. Empty path stays empty, so the index mounts the repo at `<sync-root>/<parent-project>/<repo-name>`. An absolute path stays as written. A relative path becomes absolute against the child manifest directory (the checkout root, or `local_path`). The workspace index already uses absolute paths as-is, so those checkouts stay where the child umbrella put them.
5. Deep-merge `overrides.yml` tags onto those repos. A description in the override replaces the child description.
6. Union parent `repos[]`. A parent entry with the same `name` replaces the resolved entry, including its path.
7. Parent project `tags` override child project tag keys. Parent `agent_profile` stays the parent block (existing profile merge already walks workspace → project → repo).

`config patch` and Config Studio load and save the parent file from disk. They show the imprint pointer and parent pins. They do not show expanded child repos, and they do not write `overrides.yml`.

`agent map sync` calls the resolver. An imprinted map file's first line is:

```text
# imprint id=<id> project=<child> sha=<sha> fetched_at=<iso>
```

When resolve fails (`missing_cache`, `missing_child_project`, or `unreadable_manifest`) and `agent-map/<project>.txt` already exists, sync leaves that file in place and adds the warning. When the file does not exist yet, sync writes parent pins only and a comment line with that warning.

`imprint override set` writes tags and description into `overrides.yml` for that repo name. `imprint override unset` removes one tag key, or the description when `--description` is passed with no text. Adding a repo, or changing `url` or `path`, is a parent `repos[]` pin edited in the parent manifest. `config validate` after those writes still sees a pointer, not the expanded list.

### Docs and modality

Reference: `docs/reference/imprint.md` with `<!-- modality:project_imprint -->`. Register `project_imprint` for CLI, MCP, documentation, and a short section in the `metagit-projects` skill (pull, then search; do not paste the child manifest). Example snippet in `examples/` is a parent fragment plus a fixture child manifest used by tests, not a second full workspace product.

### Tests

- Resolver: child repos appear under the parent project name; a child repo with no path mounts under the parent sync root; a child relative path is absolute against the child manifest directory; parent pin replaces the same name; override tag wins; child url is unchanged when the override file sets `url`.
- `override set` writes `overrides.yml` and does not modify the parent `.metagit.yml`.
- Resolver: missing cache yields parent `repos[]` only and warning `missing_cache`.
- Validate: derived plus imprint fails; two projects with the same `imprint.id` and different urls fail; project name `imprints` fails.
- Pull against a local git fixture writes `lock.json` with a sha and a checkout containing `.metagit.yml`.
- Push updates the child manifest tags and clears those keys from `overrides.yml`.
- Agent map sync after pull writes the imprint header and one repo line. Agent map sync without a cache does not empty an existing map file.

## Data flow

```text
.metagit.yml (pointer + pins)
        │
        ▼
ImprintResolver  ◄── .metagit/imprints/sources/<id>/checkout
        │            ◄── .metagit/imprints/projects/<parent>/overrides.yml
        ▼
effective project repos
        │
        ├─► workspace index → search, context pack, web catalog, sync
        └─► agent map sync → agent-map/*.txt + AGENTS.md fence
```

Slice 1 does not use this flow. Slice 2 reads `repos[]` directly until slice 3 switches `agent map sync` to the resolver.

## Error handling

| Case | Behavior |
|------|----------|
| Sync row raises | That row's `error` is `str(exc)` from `RepoOperationsService`. The job stays failed and keeps every row. |
| Sync job crashes before rows | `error` is the exception string. `results` is empty. |
| Source sync 422 | Panel lists `errors[]`. |
| Imprint pull, dirty checkout | No update. `dirty_checkout` is true. `state` stays whatever the last successful lock recorded, or `missing_cache` when no lock exists. |
| Imprint pull, child project name absent | Cache and lock are written. Status `missing_child_project`. Resolved view keeps parent pins only. |
| Imprint push, override repo missing in child | No write. Error names the repo. |
| Agent map sync, missing imprint cache | Existing `agent-map/<project>.txt` kept. JSON `warnings` includes `missing_cache`. |

## Implementation order

1. Slice 1 in the web job store, ops handler, `SyncDialog`, and `OpsPanel`.
2. Slice 2 agent map writer, fence editor, CLI, MCP, docs, modality.
3. Slice 3 schema, resolver, reserved name, pull/status/push/override, wire the resolver into the index and into agent map sync.

Each slice gets its own plan and is releasable without the later slices.
