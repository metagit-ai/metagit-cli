# Splitting a large manifest

An umbrella `.metagit.yml` that holds every project and the whole graph is one file every concurrent edit has to touch. A 17-project umbrella of about 6,000 lines, with `graph` around 2,250 of those lines, collided on that file in 7 of 200 merged pull requests. `includes:` keeps one logical manifest and puts each project (and optionally the graph) in its own file.

Older metagit releases do not know `includes`. They reject the root with `includes: Extra inputs are not permitted`. Split manifests need a release that contains this feature.

## Root file

`includes` is a top-level list of paths or globs, relative to the file that contains the entry. Only the root manifest (and a fragment that itself includes further files) may declare it.

```yaml
name: umbrella
kind: umbrella
includes:
  - .metagit.d/projects/*.yml
  - .metagit.d/graph/*.yml
workspace:
  description: Shared umbrella settings stay in the root.
```

The root keeps scalars and anything you do not split: `name`, `kind`, `agent_instructions`, `workspace.description`, `workspace.agent_profile`.

## Fragment files

A fragment is a YAML mapping. v1 allows:

- `workspace.projects` — appended after the root's own projects
- `graph.nodes` and `graph.relationships` — appended the same way
- `documentation` and `taskers`
- `workspace.description`, `workspace.agent_instructions`, `workspace.agent_profile`, and `graph.metadata`, but only in one file

A fragment must not set `name`, `kind`, or any other root scalar. The same project name, graph node id, or relationship tuple in two files is an error that names both `file:line` locations. Nested includes are limited to depth 3, cannot cycle, and cannot name the same file twice. Paths must stay inside the root manifest's directory: absolute paths, URLs, `..` escapes, and symlinks that resolve outside that directory are rejected. A glob that matches nothing is fine. A literal path that is missing is not.

Globs expand in lexicographic order of the POSIX path relative to the root. `metagit config split` writes an explicit ordered list instead of a glob so project order stays the order it had in the original file.

## Example layout

```text
.metagit.yml
.metagit.d/projects/billing.yml
.metagit.d/projects/identity.yml
.metagit.d/graph/nodes.yml
.metagit.d/graph/relationships.yml
```

For the 17-project umbrella, one file per project under `.metagit.d/projects/` plus the two graph files is enough. People editing different projects no longer share a file.

## Commands

```bash
# Preview, then split projects and graph. Writes nothing with --dry-run.
metagit config split -c .metagit.yml --by all --dir .metagit.d --dry-run
metagit config split -c .metagit.yml --by all --dir .metagit.d

# Merged view (default) vs the root file only
metagit config show -c .metagit.yml
metagit config show -c .metagit.yml --source

# Errors point at the fragment. --json includes a sources list.
metagit config validate -c .metagit.yml --json

# Format the root and every fragment
metagit fmt -c .metagit.yml

# One file again. --in-place strips includes from the root and leaves fragment files on disk.
metagit config flatten -c .metagit.yml
metagit config flatten -c .metagit.yml --in-place
```

`--by` is `project`, `graph`, or `all`. Project files are `<dir>/projects/<slug>.yml`. A slug collision is an error. Graph nodes and relationships go to `<dir>/graph/nodes.yml` and `relationships.yml`. Running split again on an already-split manifest changes nothing.

Editor schema for a fragment:

```bash
metagit config schema --fragment --output-path schemas/metagit_fragment.schema.json
```

## What a save does

Loads merge into one `MetagitConfig`. Saves write each entry back to the file it came from. A save that changes one project rewrites only that fragment; every other file keeps its bytes and mtime. A new project goes to `<first include directory>/<slug>.yml` when each existing project already has its own file, and the root `includes` list gains that path when a glob does not already match it. Otherwise the new project stays in the root. Deleting a project removes it from its fragment and leaves `projects: []` rather than deleting the file. Renaming a project removes the old entry and adds the new one. `metagit fmt` formats every included file.

Watchers, the session digest mtime, and MCP config summaries use the root plus every resolved fragment (`MetagitConfigManager.resolved_files`). Atlas staleness already hashes the files in the repo, so a fragment edit invalidates that fingerprint.

`workspace.projects[].sources[]` is unrelated. It syncs repositories from a provider. It does not compose the manifest.
