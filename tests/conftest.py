import os
import tempfile

import pytest
from dotenv import load_dotenv


@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Load environment variables from .env_example for all tests."""
    load_dotenv(
        dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env_example"),
        override=True,
    )


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test use."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname
