#!/usr/bin/env python3

"""
Example demonstrating the updated DetectionManager with all detection analysis results.

This example shows how DetectionManager now contains all the analysis results that were
previously in RepositoryAnalysis, including branch analysis, CI/CD analysis, and directory analysis.
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.detect import DetectionManager


def example_local_repository_analysis():
    """Demonstrate analyzing a local repository with all analysis results."""
    print("=== Local Repository Analysis ===")

    # Create DetectionManager for local path
    analysis = DetectionManager.from_path("./")
    if isinstance(analysis, Exception):
        print(f"Error creating DetectionManager: {analysis}")
        return

    print(f"Created DetectionManager for: {analysis.path}")
    print(f"Project name: {analysis.name}")
    print(f"Git repository: {analysis.is_git_repo}")

    # Run analysis
    result = analysis.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    # Display all analysis results
    print("\nAnalysis Results:")
    print("=" * 50)

    # Language detection
    if analysis.language_detection:
        print(f"Primary language: {analysis.language_detection.primary}")
        if analysis.language_detection.secondary:
            print(
                f"Secondary languages: {', '.join(analysis.language_detection.secondary)}"
            )
        if analysis.language_detection.frameworks:
            print(f"Frameworks: {', '.join(analysis.language_detection.frameworks)}")
        if analysis.language_detection.package_managers:
            print(
                f"Package managers: {', '.join(analysis.language_detection.package_managers)}"
            )
        if analysis.language_detection.build_tools:
            print(f"Build tools: {', '.join(analysis.language_detection.build_tools)}")

    # Project type detection
    if analysis.project_type_detection:
        print(f"Project type: {analysis.project_type_detection.type}")
        print(f"Domain: {analysis.project_type_detection.domain}")
        print(f"Confidence: {analysis.project_type_detection.confidence}")
        if analysis.project_type_detection.indicators:
            print(
                f"Indicators: {', '.join(analysis.project_type_detection.indicators)}"
            )

    # Branch analysis
    if analysis.branch_analysis:
        print(f"Branch strategy: {analysis.branch_analysis.strategy_guess}")
        print(f"Number of branches: {len(analysis.branch_analysis.branches)}")
        print("Branches:")
        for branch in analysis.branch_analysis.branches:
            print(f"  - {'[remote]' if branch.is_remote else '[local]'} {branch.name}")

    # CI/CD analysis
    if analysis.ci_config_analysis:
        print(f"CI/CD tool: {analysis.ci_config_analysis.detected_tool}")
        if analysis.ci_config_analysis.ci_config_path:
            print(f"CI/CD config path: {analysis.ci_config_analysis.ci_config_path}")
        print(f"Pipeline count: {analysis.ci_config_analysis.pipeline_count}")

    # Directory analysis
    if analysis.directory_summary:
        print(f"Total files: {analysis.directory_summary.num_files}")
        print(f"File types: {len(analysis.directory_summary.file_types)}")

    if analysis.directory_details:
        print(f"Detailed files: {analysis.directory_details.num_files}")
        print(f"File categories: {len(analysis.directory_details.file_types)}")

    # File analysis
    print(f"Has Docker: {analysis.has_docker}")
    print(f"Has tests: {analysis.has_tests}")
    print(f"Has docs: {analysis.has_docs}")
    print(f"Has IaC: {analysis.has_iac}")

    # Metrics
    if analysis.metrics:
        print(f"Contributors: {analysis.metrics.contributors}")
        print(f"Commit frequency: {analysis.metrics.commit_frequency}")

    # Metadata
    if analysis.metadata:
        print(f"Has CI: {analysis.metadata.has_ci}")
        print(f"Has tests: {analysis.metadata.has_tests}")
        print(f"Has docs: {analysis.metadata.has_docs}")
        print(f"Has Docker: {analysis.metadata.has_docker}")
        print(f"Has IaC: {analysis.metadata.has_iac}")

    print()


def example_remote_repository_analysis():
    """Demonstrate analyzing a remote repository."""
    print("=== Remote Repository Analysis ===")

    # Example repository URL
    repo_url = "https://github.com/octocat/Hello-World.git"

    # Create DetectionManager for remote URL
    analysis = DetectionManager.from_url(repo_url)
    if isinstance(analysis, Exception):
        print(f"Error creating DetectionManager: {analysis}")
        return

    print(f"Created DetectionManager for: {analysis.url}")
    print(f"Project name: {analysis.name}")
    print(f"Cloned to: {analysis.path}")
    print(f"Git repository: {analysis.is_git_repo}")
    print(f"Cloned: {analysis.is_cloned}")

    # Run analysis
    result = analysis.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    # Display key analysis results
    print("\nKey Analysis Results:")
    print("=" * 50)

    if analysis.language_detection:
        print(f"Primary language: {analysis.language_detection.primary}")

    if analysis.project_type_detection:
        print(f"Project type: {analysis.project_type_detection.type}")
        print(f"Domain: {analysis.project_type_detection.domain}")

    if analysis.branch_analysis:
        print(f"Branch strategy: {analysis.branch_analysis.strategy_guess}")
        print(f"Number of branches: {len(analysis.branch_analysis.branches)}")

    if analysis.ci_config_analysis:
        print(f"CI/CD tool: {analysis.ci_config_analysis.detected_tool}")

    if analysis.directory_summary:
        print(f"Total files: {analysis.directory_summary.num_files}")

    # Clean up cloned repository
    analysis.cleanup()
    print("Cleaned up cloned repository")
    print()


def example_specific_analysis():
    """Demonstrate running specific analysis methods."""
    print("=== Specific Analysis Methods ===")

    # Create DetectionManager
    analysis = DetectionManager.from_path("./")
    if isinstance(analysis, Exception):
        print(f"Error creating DetectionManager: {analysis}")
        return

    # Run specific analysis methods
    methods = ["language_detection", "project_type_detection", "branch_analysis"]

    for method in methods:
        print(f"\nRunning {method}...")
        result = analysis.run_specific(method)
        if result is not None:
            print(f"Error running {method}: {result}")
        else:
            print(f"✅ {method} completed successfully")

    print()


def example_configuration():
    """Demonstrate using different detection configurations."""
    print("=== Detection Configuration ===")

    # Create minimal configuration
    minimal_config = DetectionManagerConfig.minimal()
    print(f"Minimal config enabled methods: {minimal_config.get_enabled_methods()}")

    # Create full configuration
    full_config = DetectionManagerConfig.all_enabled()
    print(f"Full config enabled methods: {full_config.get_enabled_methods()}")

    # Create custom configuration
    custom_config = DetectionManagerConfig(
        branch_analysis_enabled=True,
        ci_config_analysis_enabled=True,
        directory_summary_enabled=False,
        directory_details_enabled=False,
    )
    print(f"Custom config enabled methods: {custom_config.get_enabled_methods()}")

    # Use custom configuration
    analysis = DetectionManager.from_path("./", config=custom_config)
    if isinstance(analysis, Exception):
        print(f"Error creating DetectionManager: {analysis}")
        return

    result = analysis.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    print("✅ Analysis completed with custom configuration")
    print()


def main():
    """Run all examples."""
    print("DetectionManager Examples")
    print("=" * 60)

    example_local_repository_analysis()
    example_remote_repository_analysis()
    example_specific_analysis()
    example_configuration()

    print("All examples completed!")


if __name__ == "__main__":
    main()
