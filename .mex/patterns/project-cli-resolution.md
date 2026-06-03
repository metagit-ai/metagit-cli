---
name: project-cli-resolution
description: Resolve workspace project context for metagit project/* CLI commands.
triggers:
  - "project list default not found"
  - "project select IndexError"
  - "resolve active project"
  - "synthetic default workspace"
---

# Project CLI resolution

## Manifest vs app config

- **`.metagit.yml` `workspace.projects[]`** — source of truth for multi-repo layout. Omit `workspace` entirely for single-repo **application** manifests; use top-level `paths` / `dependencies` and the computed **`local`** project in CLI.
- **`metagit.config.yaml` `workspace.default_project`** — optional **session preference** only. When unset, metagit resolves from the manifest.

There is **no** in-memory synthetic `default` project. Umbrella init templates may still write `name: default` **on disk** when the user chooses that template.

## Resolution (`layout_resolver.py`)

1. Explicit `-p` / `--project` wins.
2. Else app-config preference when that name exists in the manifest.
3. Else the sole manifest project.
4. Else `local` when no manifest projects exist.
5. Else `None` (multiple projects, no preference) — mutating commands error with guidance; `project list` uses catalog view.

## Interactive repo add prompts

`ProjectManager.add` prompts via `UserPrompt.prompt_for_model(ProjectPath, …)` including optional fields. Field descriptions on `ProjectPath` drive prompt labels (`Local project path`, `Remote git URL (ssh or https)`).
