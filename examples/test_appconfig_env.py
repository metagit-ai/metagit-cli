#!/usr/bin/env python

"""
Test script to verify AppConfig environment variable loading.
"""

import os
import tempfile
from pathlib import Path

from metagit.core.appconfig.models import AppConfig


def test_appconfig_env_loading():
    """Test that AppConfig loads environment variables correctly."""

    # Create a temporary .env file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write(
            """# Test environment variables
METAGIT_LLM_API_KEY=test_llm_key
METAGIT_GITHUB_TOKEN=test_github_token
METAGIT_GITHUB_URL=https://api.github.test.com
METAGIT_GITLAB_TOKEN=test_gitlab_token
METAGIT_GITLAB_URL=https://gitlab.test.com/api/v4
METAGIT_API_KEY=test_api_key
METAGIT_API_URL=https://api.test.com
METAGIT_API_VERSION=v2
"""
        )
        env_file = f.name

    try:
        # Set environment variables manually for testing
        os.environ["METAGIT_LLM_API_KEY"] = "test_llm_key"
        os.environ["METAGIT_GITHUB_TOKEN"] = "test_github_token"
        os.environ["METAGIT_GITHUB_URL"] = "https://api.github.test.com"
        os.environ["METAGIT_GITLAB_TOKEN"] = "test_gitlab_token"
        os.environ["METAGIT_GITLAB_URL"] = "https://gitlab.test.com/api/v4"
        os.environ["METAGIT_API_KEY"] = "test_api_key"
        os.environ["METAGIT_API_URL"] = "https://api.test.com"
        os.environ["METAGIT_API_VERSION"] = "v2"

        # Load AppConfig
        config = AppConfig.load()

        if isinstance(config, Exception):
            print(f"❌ Failed to load AppConfig: {config}")
            return False

        # Verify environment variables were loaded
        print("🔍 Testing AppConfig environment variable loading...")

        # Test LLM configuration
        if config.llm.api_key == "test_llm_key":
            print("✅ LLM API key loaded correctly")
        else:
            print(f"❌ LLM API key not loaded correctly: {config.llm.api_key}")
            return False

        # Test GitHub provider configuration
        if config.providers.github.api_token == "test_github_token":
            print("✅ GitHub token loaded correctly")
        else:
            print(
                f"❌ GitHub token not loaded correctly: {config.providers.github.api_token}"
            )
            return False

        if config.providers.github.base_url == "https://api.github.test.com":
            print("✅ GitHub URL loaded correctly")
        else:
            print(
                f"❌ GitHub URL not loaded correctly: {config.providers.github.base_url}"
            )
            return False

        if config.providers.github.enabled:
            print("✅ GitHub provider enabled correctly")
        else:
            print("❌ GitHub provider not enabled")
            return False

        # Test GitLab provider configuration
        if config.providers.gitlab.api_token == "test_gitlab_token":
            print("✅ GitLab token loaded correctly")
        else:
            print(
                f"❌ GitLab token not loaded correctly: {config.providers.gitlab.api_token}"
            )
            return False

        if config.providers.gitlab.base_url == "https://gitlab.test.com/api/v4":
            print("✅ GitLab URL loaded correctly")
        else:
            print(
                f"❌ GitLab URL not loaded correctly: {config.providers.gitlab.base_url}"
            )
            return False

        if config.providers.gitlab.enabled:
            print("✅ GitLab provider enabled correctly")
        else:
            print("❌ GitLab provider not enabled")
            return False

        # Test main API configuration
        if config.api_key == "test_api_key":
            print("✅ Main API key loaded correctly")
        else:
            print(f"❌ Main API key not loaded correctly: {config.api_key}")
            return False

        if config.api_url == "https://api.test.com":
            print("✅ Main API URL loaded correctly")
        else:
            print(f"❌ Main API URL not loaded correctly: {config.api_url}")
            return False

        if config.api_version == "v2":
            print("✅ Main API version loaded correctly")
        else:
            print(f"❌ Main API version not loaded correctly: {config.api_version}")
            return False

        print("\n🎉 All environment variable tests passed!")
        return True

    finally:
        # Clean up
        if os.path.exists(env_file):
            os.unlink(env_file)

        # Clean up environment variables
        for key in [
            "METAGIT_LLM_API_KEY",
            "METAGIT_GITHUB_TOKEN",
            "METAGIT_GITHUB_URL",
            "METAGIT_GITLAB_TOKEN",
            "METAGIT_GITLAB_URL",
            "METAGIT_API_KEY",
            "METAGIT_API_URL",
            "METAGIT_API_VERSION",
        ]:
            if key in os.environ:
                del os.environ[key]


if __name__ == "__main__":
    success = test_appconfig_env_loading()
    exit(0 if success else 1)
