# Metagit Development Guide

Upon making changes run the following to validate everything before submitting a PR

```bash
task format lint:fix test
```

## MCP Development Notes

- Use `metagit mcp serve` to start the MCP stdio runtime.
- Use `--root <path>` to test workspace gating against a specific folder.
- Use `--status-once` for quick diagnostics without starting the message loop.
- MCP gating states:
  - `inactive_missing_config` when `.metagit.yml` is not present
  - `inactive_invalid_config` when `.metagit.yml` fails validation
  - `active` when `.metagit.yml` loads successfully
