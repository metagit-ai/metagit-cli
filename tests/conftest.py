import os
import tempfile

import pytest
from dotenv import load_dotenv
from loguru import logger

# Windows runners often omit HOME; cold-import subprocesses still need a
# usable home + PATH (+ Windows process essentials) when env is replaced.
_COLD_IMPORT_ENV_KEYS = (
    "PATH",
    "HOME",
    "USERPROFILE",
    "USER",
    "USERNAME",
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "APPDATA",
    "LOCALAPPDATA",
    "ProgramFiles",
    "ProgramData",
    "UV_CACHE_DIR",
    "UV_PYTHON",
    "VIRTUAL_ENV",
)


def cold_import_env() -> dict[str, str]:
    """Minimal env for ``subprocess.run(..., env=...)`` cold-import checks."""
    env = {key: value for key in _COLD_IMPORT_ENV_KEYS if (value := os.environ.get(key))}
    env["PYTHONNOUSERSITE"] = "1"
    if "HOME" not in env and "USERPROFILE" in env:
        env["HOME"] = env["USERPROFILE"]
    if "USERPROFILE" not in env and "HOME" in env:
        env["USERPROFILE"] = env["HOME"]
    return env


@pytest.fixture
def cold_import_environment() -> dict[str, str]:
    """Fixture wrapper so tests need not import ``tests.conftest``."""
    return cold_import_env()


@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Load environment variables from .env_example for all tests."""
    load_dotenv(
        dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env_example"),
        override=True,
    )


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for tests to prevent file I/O errors."""
    # Set environment variable to disable file logging during tests
    os.environ["METAGIT_LOG_TO_FILE"] = "false"
    os.environ["METAGIT_LOG_LEVEL"] = "WARNING"  # Reduce log noise during tests

    # Remove all existing loguru handlers to prevent file I/O issues
    logger.remove()

    # Add a simple console handler for tests
    logger.add(
        lambda msg: None,  # Null sink to suppress output during tests
        level="WARNING",
        format="{message}",
    )


@pytest.fixture(autouse=True)
def cleanup_logging():
    """Clean up logging after each test to prevent file handle issues."""
    yield
    # Remove any handlers that might have been added during the test
    logger.remove()


@pytest.fixture(autouse=True)
def clear_agent_mode_env(monkeypatch):
    """Ensure a stray ``METAGIT_AGENT_MODE`` in the caller's shell can't leak
    into tests.

    Several CLI tests exercise interactive paths (the fuzzy-finder picker) or
    assert the default ``agent_mode`` posture. When ``METAGIT_AGENT_MODE`` is
    exported in the environment running pytest (common in agent/automation
    shells), it silently disables those paths and the tests fail spuriously.
    Clearing it per-test makes the suite env-independent. Tests that need the
    variable set it explicitly with ``monkeypatch.setenv`` after this fixture
    has run.
    """
    monkeypatch.delenv("METAGIT_AGENT_MODE", raising=False)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test use."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname
