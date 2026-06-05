---
name: graph-curator
description: |
  Maintains cross-repository graph relationships, GitNexus ingest, and group sync for workspace-wide code intelligence. Load this skill for scoped sessions.
model: inherit
tools: Read, Bash, Grep, Glob, Skill
skills:
  - metagit-graph-maintain
  - metagit-gitnexus
  - metagit-repo-impact
---

{{ include "body" }}
