#!/usr/bin/env python3
"""
Example script demonstrating the repository detection module.

This script shows how to use the RepositoryAnalysis class to analyze
both local repositories and remote git repositories.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.detect.repository import RepositoryAnalysis
from metagit.core.utils.logging import UnifiedLogger, LoggerConfig


def analyze_local_repository(path: str) -> None:
    """Analyze a local repository path."""
    print(f"\n{'='*60}")
    print(f"ANALYZING LOCAL REPOSITORY: {path}")
    print(f"{'='*60}")
    
    # Create logger
    logger = UnifiedLogger(LoggerConfig(log_level="INFO", minimal_console=True))
    
    # Analyze the repository
    analysis = RepositoryAnalysis.from_path(path, logger)
    
    if isinstance(analysis, Exception):
        print(f"❌ Analysis failed: {analysis}")
        return
    
    # Print summary
    summary = analysis.summary()
    if isinstance(summary, Exception):
        print(f"❌ Summary failed: {summary}")
    else:
        print(summary)
    
    # Convert to MetagitConfig
    config = analysis.to_metagit_config()
    if isinstance(config, Exception):
        print(f"❌ Config conversion failed: {config}")
    else:
        print(f"\n✅ Successfully created MetagitConfig:")
        print(f"   Name: {config.name}")
        print(f"   Type: {config.kind}")
        print(f"   Description: {config.description}")
        print(f"   Branch Strategy: {config.branch_strategy}")
        print(f"   Has CI/CD: {config.metadata.has_ci if config.metadata else False}")
        print(f"   Has Tests: {config.metadata.has_tests if config.metadata else False}")
        print(f"   Has Docker: {config.metadata.has_docker if config.metadata else False}")


def analyze_remote_repository(url: str) -> None:
    """Analyze a remote git repository by cloning it."""
    print(f"\n{'='*60}")
    print(f"ANALYZING REMOTE REPOSITORY: {url}")
    print(f"{'='*60}")
    
    # Create logger
    logger = UnifiedLogger(LoggerConfig(log_level="INFO", minimal_console=True))
    
    # Create temporary directory for cloning
    temp_dir = tempfile.mkdtemp(prefix="metagit_example_")
    
    try:
        # Analyze the repository
        analysis = RepositoryAnalysis.from_url(url, logger, temp_dir)
        
        if isinstance(analysis, Exception):
            print(f"❌ Analysis failed: {analysis}")
            return
        
        # Print summary
        summary = analysis.summary()
        if isinstance(summary, Exception):
            print(f"❌ Summary failed: {summary}")
        else:
            print(summary)
        
        # Convert to MetagitConfig
        config = analysis.to_metagit_config()
        if isinstance(config, Exception):
            print(f"❌ Config conversion failed: {config}")
        else:
            print(f"\n✅ Successfully created MetagitConfig:")
            print(f"   Name: {config.name}")
            print(f"   Type: {config.kind}")
            print(f"   Description: {config.description}")
            print(f"   Branch Strategy: {config.branch_strategy}")
            print(f"   Has CI/CD: {config.metadata.has_ci if config.metadata else False}")
            print(f"   Has Tests: {config.metadata.has_tests if config.metadata else False}")
            print(f"   Has Docker: {config.metadata.has_docker if config.metadata else False}")
        config.save_to_file("metagit.config.yaml")
        # Clean up
        print(f"Cleaning up temporary directory: {analysis.temp_dir}")
        #analysis.cleanup()
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        # Clean up temp directory if analysis failed
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def main():
    """Main function demonstrating repository detection."""
    print("Metagit Repository Detection Example")
    print("=" * 60)
    
    # Example 1: Analyze current directory (if it's a git repo)
    current_dir = os.getcwd()
    if os.path.exists(os.path.join(current_dir, '.git')):
        analyze_local_repository(current_dir)
    else:
        print(f"\nCurrent directory is not a git repository: {current_dir}")
    
    # Example 2: Analyze a well-known open source repository
    # Using a small, well-known repository for demonstration
    remote_url = "https://github.com/octocat/Hello-World.git"
    analyze_remote_repository(remote_url)
    
    # Example 3: Analyze another repository
    # You can uncomment and modify these lines to test with other repositories
    # analyze_remote_repository("https://github.com/python/cpython.git")
    # analyze_remote_repository("https://github.com/torvalds/linux.git")
    
    print(f"\n{'='*60}")
    print("Example completed!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main() 