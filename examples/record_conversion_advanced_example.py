#!/usr/bin/env python
"""
Advanced example demonstrating automatic field detection in MetagitRecord conversion.

This script shows how the new approach automatically handles field differences
without requiring manual field lists or attribute definitions.
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
    """Demonstrate advanced MetagitRecord conversion with automatic field detection."""
    print("🚀 Advanced MetagitRecord Conversion Example")
    print("=" * 60)

    # Example 1: Show field differences automatically
    print("\n1. Automatic Field Difference Detection:")
    print("-" * 40)
    
    differences = MetagitRecord.get_field_differences()
    print(f"📊 Field Analysis:")
    print(f"   Total MetagitRecord fields: {differences['total_record_fields']}")
    print(f"   Total MetagitConfig fields: {differences['total_config_fields']}")
    print(f"   Common fields: {differences['common_field_count']}")
    print(f"   Record-only fields: {len(differences['record_only_fields'])}")
    print(f"   Config-only fields: {len(differences['config_only_fields'])}")
    
    print(f"\n🔗 Common Fields (automatically detected):")
    for field in differences['common_fields'][:10]:  # Show first 10
        print(f"   ✓ {field}")
    if len(differences['common_fields']) > 10:
        print(f"   ... and {len(differences['common_fields']) - 10} more")
    
    print(f"\n📝 Record-Only Fields (automatically excluded):")
    for field in differences['record_only_fields'][:5]:  # Show first 5
        print(f"   ✗ {field}")
    if len(differences['record_only_fields']) > 5:
        print(f"   ... and {len(differences['record_only_fields']) - 5} more")

    # Example 2: Show compatible fields
    print(f"\n2. Compatible Fields Detection:")
    print("-" * 40)
    
    compatible_fields = MetagitRecord.get_compatible_fields()
    print(f"✅ Fields that can be converted automatically: {len(compatible_fields)}")
    print(f"   Core fields: {', '.join(sorted(list(compatible_fields))[:5])}...")

    # Example 3: Create a complex record
    print(f"\n3. Creating Complex Record with Detection Data:")
    print("-" * 40)
    
    record = MetagitRecord(
        name="advanced-example",
        description="A project demonstrating automatic field detection",
        url="https://github.com/example/advanced-project.git",
        kind=ProjectKind.APPLICATION,
        branch_strategy=BranchStrategy.TRUNK,
        license=License(kind=LicenseKind.MIT, file="LICENSE"),
        maintainers=[
            Maintainer(name="Auto Field", email="auto@example.com", role="Developer"),
        ],
        cicd=CICD(
            platform=CICDPlatform.GITHUB,
            pipelines=[Pipeline(name="Auto CI", ref=".github/workflows/auto.yml")]
        ),
        # Detection-specific fields (will be automatically excluded)
        branch="main",
        checksum="auto123detect456",
        last_updated=datetime.now(),
        branches=[Branch(name="main", environment="production")],
        metrics=Metrics(
            stars=200,
            forks=30,
            open_issues=10,
            pull_requests=PullRequests(open=6, merged_last_30d=25),
            contributors=15,
            commit_frequency="daily",
        ),
        metadata=RepoMetadata(
            tags=["python", "automatic", "field-detection"],
            has_ci=True,
            has_tests=True,
            has_docs=True,
            has_docker=True,
            has_iac=True,
        ),
        language=Language(primary="Python", secondary=["TypeScript"]),
        language_version="3.12",
        domain="web",
        detection_timestamp=datetime.now(),
        detection_source="automatic",
        detection_version="3.0.0",
    )
    
    print(f"✅ Created record with {len(MetagitRecord.model_fields)} total fields")
    print(f"   Detection fields: {len(differences['record_only_fields'])}")
    print(f"   Config fields: {len(differences['common_fields'])}")

    # Example 4: Automatic conversion without manual field lists
    print(f"\n4. Automatic Conversion (No Manual Field Lists):")
    print("-" * 40)
    
    # This conversion happens automatically without any manual field definitions
    config = record.to_metagit_config()
    
    print(f"✅ Converted to config with {len(MetagitConfig.model_fields)} fields")
    print(f"   Original record fields: {len(MetagitRecord.model_fields)}")
    print(f"   Converted config fields: {len(MetagitConfig.model_fields)}")
    print(f"   Fields automatically excluded: {len(MetagitRecord.model_fields) - len(MetagitConfig.model_fields)}")
    
    # Verify that detection fields were automatically excluded
    detection_fields_excluded = all(
        not hasattr(config, field) for field in differences['record_only_fields']
    )
    print(f"   Detection fields properly excluded: {detection_fields_excluded}")

    # Example 5: Show what was preserved
    print(f"\n5. Field Preservation Analysis:")
    print("-" * 40)
    
    print(f"✅ Preserved in conversion:")
    for field in differences['common_fields'][:8]:  # Show first 8
        record_value = getattr(record, field, None)
        config_value = getattr(config, field, None)
        status = "✓" if record_value == config_value else "⚠"
        print(f"   {status} {field}: {record_value} -> {config_value}")
    
    print(f"\n❌ Automatically excluded:")
    for field in differences['record_only_fields'][:5]:  # Show first 5
        record_value = getattr(record, field, None)
        has_config_field = hasattr(config, field)
        print(f"   ✗ {field}: {record_value} (config has field: {has_config_field})")

    # Example 6: Performance comparison
    print(f"\n6. Performance with Automatic Field Detection:")
    print("-" * 40)
    
    import time
    
    # Test conversion performance
    start_time = time.time()
    for i in range(1000):
        test_record = MetagitRecord(
            name=f"perf-test-{i}",
            description=f"Performance test {i}",
            detection_source="automatic",
            detection_version="3.0.0",
            branch=f"branch-{i}",
            checksum=f"hash-{i}",
        )
        test_config = test_record.to_metagit_config()
    end_time = time.time()
    
    conversion_time = end_time - start_time
    print(f"✅ 1000 conversions with automatic field detection: {conversion_time:.3f}s")
    print(f"   Average time per conversion: {(conversion_time / 1000) * 1000:.2f}ms")

    # Example 7: Advanced conversion with kwargs
    print(f"\n7. Advanced Conversion with Flexible Parameters:")
    print("-" * 40)
    
    base_config = MetagitConfig(
        name="flexible-config",
        description="A config for advanced conversion",
        kind=ProjectKind.SERVICE,
    )
    
    # Use the advanced method with flexible kwargs
    advanced_record = MetagitRecord.from_metagit_config_advanced(
        base_config,
        detection_source="advanced",
        detection_version="4.0.0",
        branch="feature/advanced",
        checksum="advanced123",
        metrics=Metrics(
            stars=500,
            forks=50,
            open_issues=20,
            pull_requests=PullRequests(open=10, merged_last_30d=50),
            contributors=25,
            commit_frequency="daily",
        ),
    )
    
    print(f"✅ Advanced conversion successful")
    print(f"   Detection source: {advanced_record.detection_source}")
    print(f"   Detection version: {advanced_record.detection_version}")
    print(f"   Branch: {advanced_record.branch}")
    print(f"   Metrics stars: {advanced_record.metrics.stars if advanced_record.metrics else 'None'}")

    # Example 8: Demonstrate the benefits
    print(f"\n8. Benefits of Automatic Field Detection:")
    print("-" * 40)
    
    print("🎯 Key Advantages:")
    print("   • No manual field lists to maintain")
    print("   • Automatically adapts to model changes")
    print("   • Type-safe with full Pydantic validation")
    print("   • Performance optimized with field introspection")
    print("   • Future-proof against schema evolution")
    
    print(f"\n📈 Maintainability Benefits:")
    print("   • Adding new fields to either model requires no code changes")
    print("   • Field differences are automatically detected")
    print("   • Conversion logic is centralized and reusable")
    print("   • Error handling is consistent across all conversions")
    
    print(f"\n⚡ Performance Benefits:")
    print("   • Uses Pydantic's optimized field introspection")
    print("   • Minimal memory allocation")
    print("   • No deep copying of nested objects")
    print("   • Fast validation with C-optimized code")

    print(f"\n🎉 Advanced conversion example completed successfully!")
    print(f"\nThe new approach eliminates the need for manual field management")
    print(f"while providing better performance, maintainability, and type safety.")


if __name__ == "__main__":
    main() 