import os
import tempfile

import pytest
from dotenv import load_dotenv
from loguru import logger


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


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test use."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname
