#!/usr/bin/env python3

"""
Example demonstrating the updated RepositoryAnalysis with all detection analysis results.

This example shows how RepositoryAnalysis now contains all the analysis results that were
previously in DetectionManager, including branch analysis, CI/CD analysis, and directory analysis.
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.detect.repository import RepositoryAnalysis


def example_local_repository_analysis():
    """Demonstrate analyzing a local repository with all analysis results."""
    print("=== Local Repository Analysis ===")

    # Create RepositoryAnalysis for local path
    analysis = RepositoryAnalysis.from_path("./")
    if isinstance(analysis, Exception):
        print(f"Error creating RepositoryAnalysis: {analysis}")
        return

    print(f"Created RepositoryAnalysis for: {analysis.path}")
    print(f"Project name: {analysis.name}")
    print(f"Git repository: {analysis.is_git_repo}")

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

    # Branch analysis
    if analysis.branch_analysis:
        print(f"Branch strategy: {analysis.branch_analysis.strategy_guess}")
        print(f"Number of branches: {len(analysis.branch_analysis.branches)}")
        for branch in analysis.branch_analysis.branches:
            print(f"  - {'[remote]' if branch.is_remote else '[local]'} {branch.name}")

    # CI/CD analysis
    if analysis.ci_config_analysis:
        print(f"CI/CD tool: {analysis.ci_config_analysis.detected_tool}")
        if analysis.ci_config_analysis.detected_tools:
            print(
                f"Detected tools: {', '.join(analysis.ci_config_analysis.detected_tools)}"
            )

    # Directory analysis
    if analysis.directory_summary:
        print(f"Total files: {analysis.directory_summary.num_files}")
        print(f"File types: {len(analysis.directory_summary.file_types)}")
        for file_type in analysis.directory_summary.file_types[:5]:  # Show first 5
            print(f"  - {file_type.type}: {file_type.count} files")

    if analysis.directory_details:
        print(f"Detailed files: {analysis.directory_details.num_files}")
        print(f"File categories: {len(analysis.directory_details.file_types)}")
        for category, types in analysis.directory_details.file_types.items():
            print(f"  - {category}: {len(types)} types")

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
        print(f"Default branch: {analysis.metadata.default_branch}")
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

    # Create RepositoryAnalysis for remote URL
    analysis = RepositoryAnalysis.from_url(repo_url)
    if isinstance(analysis, Exception):
        print(f"Error creating RepositoryAnalysis: {analysis}")
        return

    print(f"Created RepositoryAnalysis for: {analysis.url}")
    print(f"Project name: {analysis.name}")
    print(f"Cloned to: {analysis.path}")
    print(f"Git repository: {analysis.is_git_repo}")
    print(f"Cloned: {analysis.is_cloned}")

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


def example_metagit_record_conversion():
    """Demonstrate converting RepositoryAnalysis to MetagitRecord."""
    print("=== MetagitRecord Conversion ===")

    # Create RepositoryAnalysis
    analysis = RepositoryAnalysis.from_path("./")
    if isinstance(analysis, Exception):
        print(f"Error creating RepositoryAnalysis: {analysis}")
        return

    # Convert to MetagitRecord
    record = analysis.to_metagit_record()
    if isinstance(record, Exception):
        print(f"Error converting to MetagitRecord: {record}")
        return

    print("Successfully converted to MetagitRecord")
    print(f"Record name: {record.name}")
    print(f"Record description: {record.description}")
    print(f"Record URL: {record.url}")
    print(f"Record kind: {record.kind}")
    print(f"Record domain: {record.domain}")
    print(f"Record language: {record.language}")
    print(f"Record branch strategy: {record.branch_strategy}")
    print(f"Record detection timestamp: {record.detection_timestamp}")
    print(f"Record detection source: {record.detection_source}")
    print(f"Record detection version: {record.detection_version}")

    print()


def example_metagit_config_conversion():
    """Demonstrate converting RepositoryAnalysis to MetagitConfig."""
    print("=== MetagitConfig Conversion ===")

    # Create RepositoryAnalysis
    analysis = RepositoryAnalysis.from_path("./")
    if isinstance(analysis, Exception):
        print(f"Error creating RepositoryAnalysis: {analysis}")
        return

    # Convert to MetagitConfig
    config = analysis.to_metagit_config()
    if isinstance(config, Exception):
        print(f"Error converting to MetagitConfig: {config}")
        return

    print("Successfully converted to MetagitConfig")
    print(f"Config name: {config.name}")
    print(f"Config description: {config.description}")
    print(f"Config URL: {config.url}")
    print(f"Config kind: {config.kind}")
    print(f"Config domain: {config.domain}")
    print(f"Config language: {config.language}")
    print(f"Config branch strategy: {config.branch_strategy}")

    print()


def example_summary_output():
    """Demonstrate summary output."""
    print("=== Summary Output ===")

    # Create RepositoryAnalysis
    analysis = RepositoryAnalysis.from_path("./")
    if isinstance(analysis, Exception):
        print(f"Error creating RepositoryAnalysis: {analysis}")
        return

    # Generate summary
    summary = analysis.summary()
    if isinstance(summary, Exception):
        print(f"Error generating summary: {summary}")
        return

    print("Repository Analysis Summary:")
    print("=" * 50)
    print(summary)
    print()


def example_serialization():
    """Demonstrate serialization of RepositoryAnalysis."""
    print("=== Serialization ===")

    # Create RepositoryAnalysis
    analysis = RepositoryAnalysis.from_path("./")
    if isinstance(analysis, Exception):
        print(f"Error creating RepositoryAnalysis: {analysis}")
        return

    # Convert to MetagitRecord for serialization
    record = analysis.to_metagit_record()
    if isinstance(record, Exception):
        print(f"Error converting to MetagitRecord: {record}")
        return

    # Serialize to YAML
    yaml_output = record.to_yaml()
    if isinstance(yaml_output, Exception):
        print(f"Error serializing to YAML: {yaml_output}")
        return

    print("YAML Output (first 500 characters):")
    print("=" * 50)
    print(yaml_output[:500] + "..." if len(yaml_output) > 500 else yaml_output)
    print()

    # Serialize to JSON
    json_output = record.to_json()
    if isinstance(json_output, Exception):
        print(f"Error serializing to JSON: {json_output}")
        return

    print("JSON Output (first 500 characters):")
    print("=" * 50)
    print(json_output[:500] + "..." if len(json_output) > 500 else json_output)
    print()


def main():
    """Run all examples."""
    print("RepositoryAnalysis Examples")
    print("=" * 60)
    print()

    # Run examples
    example_local_repository_analysis()
    example_metagit_record_conversion()
    example_metagit_config_conversion()
    example_summary_output()
    example_serialization()

    # Note: Remote analysis is commented out to avoid cloning during examples
    # Uncomment the line below to test remote repository analysis
    # example_remote_repository_analysis()

    print("All examples completed!")


if __name__ == "__main__":
    main()
