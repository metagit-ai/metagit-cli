#!/usr/bin/env python3

"""
Example demonstrating the updated DetectionManager that uses RepositoryAnalysis for all detection details.

This example shows how DetectionManager now uses RepositoryAnalysis as the single source for all
detection analysis results while maintaining the MetagitRecord interface.
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.detect.manager import DetectionManager, DetectionManagerConfig


def example_local_repository_analysis():
    """Demonstrate analyzing a local repository."""
    print("=== Local Repository Analysis ===")

    # Create DetectionManager for local path
    manager = DetectionManager.from_path("./")
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    print(f"Created DetectionManager for: {manager.path}")
    print(f"Project name: {manager.name}")
    print(f"Detection source: {manager.detection_source}")

    # Run all analyses
    result = manager.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    print("Analysis completed successfully!")
    print(f"Detection timestamp: {manager.detection_timestamp}")
    print()


def example_remote_repository_analysis():
    """Demonstrate analyzing a remote repository."""
    print("=== Remote Repository Analysis ===")

    # Example repository URL
    repo_url = "https://github.com/octocat/Hello-World.git"

    # Create DetectionManager for remote URL
    manager = DetectionManager.from_url(repo_url)
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    print(f"Created DetectionManager for: {manager.url}")
    print(f"Project name: {manager.name}")
    print(f"Detection source: {manager.detection_source}")

    # Run all analyses
    result = manager.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    print("Analysis completed successfully!")
    print(f"Detection timestamp: {manager.detection_timestamp}")

    # Clean up cloned repository
    manager.cleanup()
    print()


def example_configuration_options():
    """Demonstrate different configuration options."""
    print("=== Configuration Options ===")

    # Minimal configuration
    print("Minimal configuration:")
    config = DetectionManagerConfig.minimal()
    manager = DetectionManager.from_path("./", config=config)
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    print(f"Enabled methods: {', '.join(config.get_enabled_methods())}")
    print()

    # All enabled configuration
    print("All enabled configuration:")
    config = DetectionManagerConfig.all_enabled()
    manager = DetectionManager.from_path("./", config=config)
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    print(f"Enabled methods: {', '.join(config.get_enabled_methods())}")
    print()

    # Custom configuration
    print("Custom configuration:")
    config = DetectionManagerConfig(
        branch_analysis_enabled=True,
        ci_config_analysis_enabled=True,
        directory_summary_enabled=False,
        directory_details_enabled=False,
        commit_analysis_enabled=False,
        tag_analysis_enabled=False,
    )
    manager = DetectionManager.from_path("./", config=config)
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    print(f"Enabled methods: {', '.join(config.get_enabled_methods())}")
    print()


def example_metagit_record_integration():
    """Demonstrate MetagitRecord integration."""
    print("=== MetagitRecord Integration ===")

    # Create DetectionManager
    manager = DetectionManager.from_path("./")
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    # Run analysis
    result = manager.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    # Access MetagitRecord fields
    print("MetagitRecord fields:")
    print(f"  Name: {manager.name}")
    print(f"  Description: {manager.description}")
    print(f"  Kind: {manager.kind}")
    print(f"  Domain: {manager.domain}")
    print(f"  Language: {manager.language}")
    print(f"  Language Version: {manager.language_version}")
    print(f"  Branch Strategy: {manager.branch_strategy}")
    print(f"  URL: {manager.url}")
    print(f"  Path: {manager.path}")

    # Access detection-specific fields
    print("\nDetection-specific fields:")
    print(f"  Detection Timestamp: {manager.detection_timestamp}")
    print(f"  Detection Source: {manager.detection_source}")
    print(f"  Detection Version: {manager.detection_version}")
    print(f"  Analysis Completed: {manager.analysis_completed}")

    # Access RepositoryAnalysis results
    if manager.repository_analysis:
        print("\nRepositoryAnalysis results:")
        print(
            f"  Has Branch Analysis: {manager.repository_analysis.branch_analysis is not None}"
        )
        print(
            f"  Has CI/CD Analysis: {manager.repository_analysis.ci_config_analysis is not None}"
        )
        print(
            f"  Has Directory Summary: {manager.repository_analysis.directory_summary is not None}"
        )
        print(
            f"  Has Directory Details: {manager.repository_analysis.directory_details is not None}"
        )

        # Access specific analysis results
        if manager.repository_analysis.branch_analysis:
            print(
                f"  Branch Strategy Guess: {manager.repository_analysis.branch_analysis.strategy_guess}"
            )
            print(
                f"  Number of Branches: {len(manager.repository_analysis.branch_analysis.branches)}"
            )

        if manager.repository_analysis.ci_config_analysis:
            print(
                f"  CI/CD Tool: {manager.repository_analysis.ci_config_analysis.detected_tool}"
            )

        if manager.repository_analysis.directory_summary:
            print(
                f"  Total Files: {manager.repository_analysis.directory_summary.num_files}"
            )
            print(
                f"  File Types: {len(manager.repository_analysis.directory_summary.file_types)}"
            )

    print()


def example_output_formats():
    """Demonstrate different output formats."""
    print("=== Output Formats ===")

    # Create DetectionManager
    manager = DetectionManager.from_path("./")
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    # Run analysis
    result = manager.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    # Summary output
    summary = manager.summary()
    if isinstance(summary, Exception):
        print(f"Error getting summary: {summary}")
    else:
        print("Summary output:")
        print(summary[:200] + "..." if len(summary) > 200 else summary)
        print()

    # YAML output (includes all detection data)
    yaml_output = manager.to_yaml()
    if isinstance(yaml_output, Exception):
        print(f"Error converting to YAML: {yaml_output}")
    else:
        print("YAML output (first 200 chars):")
        print(yaml_output[:200] + "..." if len(yaml_output) > 200 else yaml_output)
        print()

    # JSON output (includes all detection data)
    json_output = manager.to_json()
    if isinstance(json_output, Exception):
        print(f"Error converting to JSON: {json_output}")
    else:
        print("JSON output (first 200 chars):")
        print(json_output[:200] + "..." if len(json_output) > 200 else json_output)
        print()


def example_specific_analysis_methods():
    """Demonstrate running specific analysis methods."""
    print("=== Specific Analysis Methods ===")

    # Create DetectionManager with minimal config
    config = DetectionManagerConfig.minimal()
    manager = DetectionManager.from_path("./", config=config)
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    # Run specific methods
    methods = ["branch_analysis", "ci_config_analysis"]

    for method in methods:
        print(f"Running {method}...")
        result = manager.run_specific(method)
        if result is not None:
            print(f"Error running {method}: {result}")
        else:
            print(f"✅ {method} completed successfully")

    # Test disabled method
    print("Testing disabled method...")
    result = manager.run_specific("directory_summary")
    if isinstance(result, Exception):
        print(f"✅ Correctly rejected disabled method: {result}")
    else:
        print("❌ Should have rejected disabled method")

    print()


def example_repository_analysis_access():
    """Demonstrate direct access to RepositoryAnalysis."""
    print("=== RepositoryAnalysis Access ===")

    # Create DetectionManager
    manager = DetectionManager.from_path("./")
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    # Run analysis
    result = manager.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    # Access RepositoryAnalysis directly
    if manager.repository_analysis:
        repo_analysis = manager.repository_analysis

        print("Direct RepositoryAnalysis access:")
        print(f"  Path: {repo_analysis.path}")
        print(f"  Name: {repo_analysis.name}")
        print(f"  Is Git Repo: {repo_analysis.is_git_repo}")
        print(f"  Is Cloned: {repo_analysis.is_cloned}")

        # Access language detection
        if repo_analysis.language_detection:
            print(f"  Primary Language: {repo_analysis.language_detection.primary}")
            if repo_analysis.language_detection.secondary:
                print(
                    f"  Secondary Languages: {', '.join(repo_analysis.language_detection.secondary)}"
                )

        # Access project type detection
        if repo_analysis.project_type_detection:
            print(f"  Project Type: {repo_analysis.project_type_detection.type}")
            print(f"  Domain: {repo_analysis.project_type_detection.domain}")
            print(f"  Confidence: {repo_analysis.project_type_detection.confidence}")

        # Access file analysis
        print(f"  Has Docker: {repo_analysis.has_docker}")
        print(f"  Has Tests: {repo_analysis.has_tests}")
        print(f"  Has Docs: {repo_analysis.has_docs}")
        print(f"  Has IaC: {repo_analysis.has_iac}")

        # Access metrics
        if repo_analysis.metrics:
            print(f"  Contributors: {repo_analysis.metrics.contributors}")
            print(f"  Commit Frequency: {repo_analysis.metrics.commit_frequency}")

    print()


def main():
    """Run all examples."""
    print("DetectionManager Examples")
    print("=" * 60)
    print()

    # Run examples
    example_local_repository_analysis()
    example_configuration_options()
    example_metagit_record_integration()
    example_output_formats()
    example_specific_analysis_methods()
    example_repository_analysis_access()

    # Note: Remote analysis is commented out to avoid cloning during examples
    # Uncomment the line below to test remote repository analysis
    # example_remote_repository_analysis()

    print("All examples completed!")


if __name__ == "__main__":
    main()
