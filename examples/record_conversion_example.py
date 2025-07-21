#!/usr/bin/env python
"""
Example script demonstrating fast conversion between MetagitRecord and MetagitConfig.

This script shows how to use the latest Pydantic best practices for efficient
conversion between MetagitRecord and MetagitConfig data structures.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from metagit.core.config.models import (
    Branch,
    BranchStrategy,
    CICD,
    CICDPlatform,
    Language,
    License,
    LicenseKind,
    Maintainer,
    Metrics,
    MetagitConfig,
    Pipeline,
    PullRequests,
    RepoMetadata,
)
from metagit.core.project.models import ProjectKind
from metagit.core.record.models import MetagitRecord


def main():
    """Demonstrate MetagitRecord conversion methods."""
    print("🚀 MetagitRecord Conversion Example")
    print("=" * 50)

    # Example 1: Create a MetagitConfig
    print("\n1. Creating a MetagitConfig...")
    config = MetagitConfig(
        name="example-project",
        description="A comprehensive example project",
        url="https://github.com/example/project.git",
        kind=ProjectKind.APPLICATION,
        branch_strategy=BranchStrategy.TRUNK,
        license=License(kind=LicenseKind.MIT, file="LICENSE"),
        maintainers=[
            Maintainer(
                name="Alice Developer", email="alice@example.com", role="Lead Developer"
            ),
            Maintainer(
                name="Bob Maintainer", email="bob@example.com", role="Maintainer"
            ),
        ],
        cicd=CICD(
            platform=CICDPlatform.GITHUB,
            pipelines=[
                Pipeline(name="CI", ref=".github/workflows/ci.yml"),
                Pipeline(name="CD", ref=".github/workflows/cd.yml"),
            ],
        ),
    )
    print(f"✅ Created MetagitConfig: {config.name}")

    # Example 2: Convert MetagitConfig to MetagitRecord
    print("\n2. Converting MetagitConfig to MetagitRecord...")
    record = MetagitRecord.from_metagit_config(
        config,
        detection_source="github",
        detection_version="2.0.0",
        additional_detection_data={
            "branch": "main",
            "checksum": "abc123def456",
            "metrics": Metrics(
                stars=150,
                forks=25,
                open_issues=8,
                pull_requests=PullRequests(open=5, merged_last_30d=20),
                contributors=12,
                commit_frequency="daily",
            ),
            "metadata": RepoMetadata(
                tags=["python", "fastapi", "postgresql"],
                has_ci=True,
                has_tests=True,
                has_docs=True,
                has_docker=True,
                has_iac=True,
            ),
            "language": Language(
                primary="Python", secondary=["JavaScript", "TypeScript"]
            ),
            "language_version": "3.11",
            "domain": "web",
        },
    )
    print(f"✅ Created MetagitRecord with detection data")

    # Example 3: Show detection summary
    print("\n3. Detection Summary:")
    summary = record.get_detection_summary()
    for key, value in summary.items():
        if key == "metrics":
            print(f"  {key}:")
            for metric_key, metric_value in value.items():
                print(f"    {metric_key}: {metric_value}")
        elif key == "metadata":
            print(f"  {key}:")
            for meta_key, meta_value in value.items():
                print(f"    {meta_key}: {meta_value}")
        else:
            print(f"  {key}: {value}")

    # Example 4: Convert MetagitRecord back to MetagitConfig
    print("\n4. Converting MetagitRecord back to MetagitConfig...")
    converted_config = record.to_metagit_config()
    print(f"✅ Converted back to MetagitConfig: {converted_config.name}")

    # Example 5: Verify round-trip conversion
    print("\n5. Verifying round-trip conversion...")
    print(f"  Original config name: {config.name}")
    print(f"  Converted config name: {converted_config.name}")
    print(f"  Names match: {config.name == converted_config.name}")
    print(f"  Descriptions match: {config.description == converted_config.description}")
    print(f"  Kinds match: {config.kind == converted_config.kind}")
    print(
        f"  Branch strategies match: {config.branch_strategy == converted_config.branch_strategy}"
    )

    # Example 6: Performance test
    print("\n6. Performance test (1000 conversions)...")
    import time

    start_time = time.time()
    for i in range(1000):
        test_config = MetagitConfig(name=f"perf-test-{i}")
        test_record = MetagitRecord.from_metagit_config(test_config)
        back_to_config = test_record.to_metagit_config()
    end_time = time.time()

    conversion_time = end_time - start_time
    print(f"✅ Completed 1000 round-trip conversions in {conversion_time:.3f} seconds")
    print(f"   Average time per conversion: {(conversion_time / 1000) * 1000:.2f} ms")

    # Example 7: Complex nested object conversion
    print("\n7. Complex nested object conversion...")
    complex_config = MetagitConfig(
        name="complex-project",
        description="A project with complex nested objects",
        kind=ProjectKind.SERVICE,
        branch_strategy=BranchStrategy.GITHUBFLOW,
        license=License(kind=LicenseKind.APACHE_2_0, file="LICENSE"),
        maintainers=[
            Maintainer(
                name="Complex Alice", email="alice@complex.com", role="Architect"
            ),
            Maintainer(name="Complex Bob", email="bob@complex.com", role="Developer"),
            Maintainer(name="Complex Carol", email="carol@complex.com", role="DevOps"),
        ],
        cicd=CICD(
            platform=CICDPlatform.GITLAB,
            pipelines=[
                Pipeline(name="Build", ref=".gitlab-ci.yml"),
                Pipeline(name="Test", ref=".gitlab-ci-test.yml"),
                Pipeline(name="Deploy", ref=".gitlab-ci-deploy.yml"),
            ],
        ),
    )

    complex_record = MetagitRecord.from_metagit_config(
        complex_config,
        detection_source="gitlab",
        detection_version="3.0.0",
    )

    back_to_complex_config = complex_record.to_metagit_config()

    print(f"✅ Complex conversion successful")
    print(f"  Maintainers preserved: {len(back_to_complex_config.maintainers)}")
    print(f"  Pipelines preserved: {len(back_to_complex_config.cicd.pipelines)}")
    print(f"  Platform preserved: {back_to_complex_config.cicd.platform}")

    # Example 8: Error handling demonstration
    print("\n8. Error handling demonstration...")
    try:
        # This should work fine
        minimal_config = MetagitConfig(name="minimal")
        minimal_record = MetagitRecord.from_metagit_config(minimal_config)
        back_to_minimal = minimal_record.to_metagit_config()
        print("✅ Minimal conversion successful")
    except Exception as e:
        print(f"❌ Minimal conversion failed: {e}")

    print("\n🎉 All conversion examples completed successfully!")
    print("\nKey Benefits of this implementation:")
    print("  • Fast conversion using Pydantic's optimized validation")
    print("  • Type-safe with proper error handling")
    print("  • Memory efficient with minimal object copying")
    print("  • Supports complex nested objects")
    print("  • Maintains data integrity through round-trip conversion")
    print("  • Provides detection data summary for quick analysis")


if __name__ == "__main__":
    main()
