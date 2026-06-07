# Overlay: orchestration-overseer

Team-committed agent template customizations for this workspace.

- **Commit** this `.metagit-agents/` tree to git so the team shares it.
- `template.yaml` fields deep-merge with the bundle; lists replace bundled lists.
- `.tpl` files here override bundled files with the same name.
- Run `metagit agent validate --root <manifest-root>` after edits.
