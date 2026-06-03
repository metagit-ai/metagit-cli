---
name: github-gh-auth
description: Avoid gh CLI 401 errors from stale GH_TOKEN / GITHUB_TOKEN env vars.
triggers:
  - "gh pr create"
  - "HTTP 401 Bad credentials"
  - "GH_TOKEN invalid"
---

# GitHub CLI auth (local)

## Problem

`gh` prefers `GH_TOKEN` / `GITHUB_TOKEN` over the keyring credential. Stale or invalid values in the environment produce `HTTP 401: Bad credentials` while `gh auth status` still lists a valid keyring login as inactive.

## Fix

Prefix `gh` commands:

```bash
env -u GH_TOKEN -u GITHUB_TOKEN gh pr create --title "..." --body "..."
```

Push uses git/SSH and does not need this unset unless git also picks up a bad helper token.

## Verify

```bash
env -u GH_TOKEN -u GITHUB_TOKEN gh auth status
```

Active account should be `true` on the keyring entry.
