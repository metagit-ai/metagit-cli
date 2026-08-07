---
name: metagit-stamp
description: Stamp or refresh a non-umbrella .metagit.yml for a target folder (git or local) using detection-first, idempotent updates. Use when users ask to create/update a local project manifest quickly.
---

# Manifest Stamping (Non-Umbrella)

Use this skill to create or refresh a project-local `.metagit.yml` for a target folder that should behave like a lightweight atlas.

## Use when

- User asks to create a new local `.metagit.yml` for an app/repo folder
- User asks to refresh stale metadata in an existing non-umbrella manifest
- User wants an idempotent detect-and-update flow rather than hand-editing every field

## Workflow

1. Resolve the target folder and verify it exists.
2. Ensure a base manifest exists in that folder:
   - if missing: initialize one
   - if present: keep it and refresh
3. Run repository detection for auto-filled metadata.
4. Persist the result to `.metagit.yml` in the target folder.
5. Validate and report what changed.

## Commands

Run from the target folder unless an explicit path is provided.

```bash
# initialize only when missing
metagit init

# detect + save (idempotent refresh)
metagit detect repository --path . --save --force --config-path .metagit.yml --output summary

# validate stamped manifest
metagit config validate --config-path .metagit.yml
```

Path-targeted variant:

```bash
metagit detect repository --path /path/to/target --save --force --config-path /path/to/target/.metagit.yml --output summary
metagit config validate --config-path /path/to/target/.metagit.yml
```

## Output contract

Return:
- target path
- whether manifest was created or refreshed
- detection mode used (`detect repository --save`)
- validation result
- key stamped fields (name/kind/language/framework/package manager, if detected)

## Safety

- This skill is for non-umbrella project manifests, not workspace controller manifests.
- Do not overwrite unrelated files; only update `.metagit.yml`.
- Prefer idempotent refreshes over destructive resets.
- If the user needs multi-repo workspace orchestration, switch to `metagit-projects` instead.
