---
name: catalog-bootstrapper
description: |
  Registers projects and repos in the workspace manifest using search-before-create.
model: inherit
tools: Read, Write, Bash, Grep, Glob, Skill
skills:
  - metagit-projects
  - metagit-bootstrap
  - metagit-config-refresh
  - metagit-cli
---

{{ include "body" }}
