# Manifest field paths

`metagit config set`, `metagit config patch`, and `metagit config preview` accept the same path syntax.

- `workspace.projects[name=billing].repos[name=api].description` selects by `name`. Documentation entries match `name` or, when they have no name, `title`.
- `graph.nodes[id=github://acme/api]` and `graph.relationships[id=edge-1]` select by `id`.
- `workspace.projects[0]` and `workspace.projects.0` are positional indexes. `set` accepts both. `patch` and `preview` accept `[n]` and the name/id selectors.

No match, or more than one match, is an error and lists the candidates. The write goes to the fragment that owns the entry and rewrites only the changed lines.
