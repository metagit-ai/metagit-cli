#!/usr/bin/env python
"""
Workspace root resolution for Metagit MCP runtime.
"""

import os
from pathlib import Path
from typing import Optional


class WorkspaceRootResolver:
    """Resolve workspace root for `.metagit.yml` gating."""

    _config_file_name: str = ".metagit.yml"
    _env_var_name: str = "METAGIT_WORKSPACE_ROOT"

    def resolve(self, cwd: str, cli_root: Optional[str] = None) -> Optional[str]:
        """Resolve workspace root by env var, CLI option, then upward walk."""
        env_root = os.getenv(self._env_var_name)
        if env_root:
            return str(Path(env_root).expanduser().resolve())

        if cli_root:
            return str(Path(cli_root).expanduser().resolve())

        return self._walk_for_config(cwd=cwd)

    def _walk_for_config(self, cwd: str) -> Optional[str]:
        """Walk up the directory tree until `.metagit.yml` is found."""
        current = Path(cwd).expanduser().resolve()
        while True:
            config_path = os.path.join(str(current), self._config_file_name)
            if os.path.exists(config_path):
                return str(current)

            if current.parent == current:
                return None

            current = current.parent
