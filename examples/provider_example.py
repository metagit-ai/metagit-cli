#!/usr/bin/env python3
import os
import sys
from pathlib import Path

from metagit.core.detect import DetectionManager
from metagit.core.providers import registry
from metagit.core.providers.github import GitHubProvider
from metagit.core.providers.gitlab import GitLabProvider

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

"""
Example script demonstrating git provider plugins for repository analysis.

This script shows how to:
1. Configure providers using AppConfig
2. Configure providers using environment variables
3. Analyze repositories with real metrics from APIs
4. Compare different configuration methods
"""


def setup_providers_from_appconfig():
    """Setup git provider plugins using AppConfig."""
    print("🔧 Setting up providers from AppConfig...")

    try:
        from metagit.core.appconfig import AppConfig

        app_config = AppConfig.load()

        if isinstance(app_config, Exception):
            print(f"❌ Failed to load AppConfig: {app_config}")
            return False

        registry.configure_from_app_config(app_config)

        providers = registry.get_all_providers()
        if providers:
            provider_names = [p.get_name() for p in providers]
            print(
                f"✅ Configured providers from AppConfig: {', '.join(provider_names)}"
            )
            return True
        else:
            print("⚠️  No providers configured in AppConfig")
            return False

    except ImportError:
        print("❌ AppConfig not available")
        return False


def setup_providers_from_environment():
    """Setup git provider plugins using environment variables."""
    print("🔧 Setting up providers from environment variables...")

    registry.configure_from_environment()

    providers = registry.get_all_providers()
    if providers:
        provider_names = [p.get_name() for p in providers]
        print(f"✅ Configured providers from environment: {', '.join(provider_names)}")
        return True
    else:
        print("⚠️  No providers configured in environment")
        return False


def setup_providers_manually():
    """Setup git provider plugins manually."""
    print("🔧 Setting up providers manually...")

    # GitHub provider
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        github_provider = GitHubProvider(api_token=github_token)
        registry.register(github_provider)
        print("✅ GitHub provider configured manually")

    # GitLab provider
    gitlab_token = os.getenv("GITLAB_TOKEN")
    if gitlab_token:
        gitlab_provider = GitLabProvider(api_token=gitlab_token)
        registry.register(gitlab_provider)
        print("✅ GitLab provider configured manually")

    providers = registry.get_all_providers()
    if providers:
        provider_names = [p.get_name() for p in providers]
        print(f"📊 Available providers: {', '.join(provider_names)}")
        return True
    else:
        print("⚠️  No providers configured")
        return False


def analyze_local_repo(repo_path: str):
    """Analyze a local repository."""
    print(f"\n🔍 Analyzing local repository: {repo_path}")

    analysis = DetectionManager.from_path(repo_path)
    if isinstance(analysis, Exception):
        print(f"❌ Analysis failed: {analysis}")
        return

    print("\n📋 Analysis Summary:")
    summary = analysis.summary()
    if isinstance(summary, Exception):
        print(f"❌ Summary failed: {summary}")
        return

    print(summary)

    # Show metrics details
    if analysis.metrics:
        print("\n📊 Metrics Details:")
        print(f"  Stars: {analysis.metrics.stars}")
        print(f"  Forks: {analysis.metrics.forks}")
        print(f"  Open Issues: {analysis.metrics.open_issues}")
        print(f"  Contributors: {analysis.metrics.contributors}")
        print(f"  Commit Frequency: {analysis.metrics.commit_frequency.value}")
        print(f"  Open PRs: {analysis.metrics.pull_requests.open}")
        print(f"  PRs Merged (30d): {analysis.metrics.pull_requests.merged_last_30d}")


def analyze_remote_repo(repo_url: str):
    """Analyze a remote repository by cloning it."""
    print(f"\n🌐 Analyzing remote repository: {repo_url}")

    analysis = DetectionManager.from_url(repo_url)
    if isinstance(analysis, Exception):
        print(f"❌ Analysis failed: {analysis}")
        return

    print("\n📋 Analysis Summary:")
    summary = analysis.summary()
    if isinstance(summary, Exception):
        print(f"❌ Summary failed: {summary}")
        return

    print(summary)

    # Clean up
    analysis.cleanup()


def demonstrate_configuration_methods():
    """Demonstrate different configuration methods."""
    print("🚀 Git Provider Plugin Configuration Examples")
    print("=" * 60)

    # Method 1: AppConfig
    print("\n📋 Method 1: AppConfig Configuration")
    print("-" * 40)
    success = setup_providers_from_appconfig()
    if success:
        print("✅ AppConfig configuration successful")
    else:
        print("❌ AppConfig configuration failed")

    # Clear providers for next method
    registry.clear()

    # Method 2: Environment Variables
    print("\n📋 Method 2: Environment Variables")
    print("-" * 40)
    success = setup_providers_from_environment()
    if success:
        print("✅ Environment configuration successful")
    else:
        print("❌ Environment configuration failed")

    # Clear providers for next method
    registry.clear()

    # Method 3: Manual Configuration
    print("\n📋 Method 3: Manual Configuration")
    print("-" * 40)
    success = setup_providers_manually()
    if success:
        print("✅ Manual configuration successful")
    else:
        print("❌ Manual configuration failed")


def main():
    """Main example function."""
    print("🚀 Git Provider Plugin Example")
    print("=" * 50)

    # Demonstrate configuration methods
    demonstrate_configuration_methods()

    # Setup providers for analysis (using AppConfig if available, otherwise environment)
    print("\n" + "=" * 50)
    print("🔧 Setting up providers for analysis...")

    # Try AppConfig first, fall back to environment
    if not setup_providers_from_appconfig():
        setup_providers_from_environment()

    # Example 1: Analyze current directory
    print("\n" + "=" * 50)
    print("Example 1: Analyzing current directory")
    analyze_local_repo(".")

    # Example 2: Analyze a specific local repository
    # Uncomment and modify the path as needed
    # print("\n" + "=" * 50)
    # print("Example 2: Analyzing specific local repository")
    # analyze_local_repo("/path/to/your/repo")

    # Example 3: Analyze a remote repository
    # Uncomment and modify the URL as needed
    # print("\n" + "=" * 50)
    # print("Example 3: Analyzing remote repository")
    # analyze_remote_repo("https://github.com/username/repo")

    print("\n" + "=" * 50)
    print("✅ Example completed!")


if __name__ == "__main__":
    main()
