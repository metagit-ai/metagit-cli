# metagit-detect

Agent code used to automatically detect a project repository for situational awareness elements including:

- Project Purpose
- Primary language
- CICD platform
- CI
  - Tools for:
    - Lint
    - SAST/DAST
    - Code Quality
    - Build
- CD 
  - Tools for:
    - Infrastructure as code
    - Configuration as code
    - Artifact deployment targets
- Development requirements
- CICD dependencies
- Monorepo subprojects
- Outside Dependencies
- Upstream related projects
- Branch management strategy
- Version management strategy
- Generated Artifacts

# Configuration

`./.configure.sh`


# Use

```bash
uv run -m metagit_detect.cli

# Show current config
uv run -m metagit_detect.cli appconfig show

# Dump new/default config
uv run -m metagit_detect.cli appconfig create

# Run generic detection for current path
uv run -m metagit_detect.cli detect repo
```