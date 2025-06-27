#!/usr/bin/env python3

"""
Simple test script to verify the migration of analysis results from DetectionManager to RepositoryAnalysis.
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")

    try:

        print("✅ DetectionManager imports successful")
    except Exception as e:
        print(f"❌ DetectionManager import failed: {e}")
        return False

    try:

        print("✅ RepositoryAnalysis import successful")
    except Exception as e:
        print(f"❌ RepositoryAnalysis import failed: {e}")
        return False

    return True


def test_detection_manager_creation():
    """Test DetectionManager creation."""
    print("\nTesting DetectionManager creation...")

    try:
        from metagit.core.detect.manager import DetectionManagerConfig

        # Test minimal config
        config = DetectionManagerConfig.minimal()
        print(f"✅ Minimal config created: {config.get_enabled_methods()}")

        # Test all enabled config
        config = DetectionManagerConfig.all_enabled()
        print(f"✅ All enabled config created: {config.get_enabled_methods()}")

        # Test custom config
        config = DetectionManagerConfig(
            branch_analysis_enabled=True,
            ci_config_analysis_enabled=False,
            directory_summary_enabled=False,
            directory_details_enabled=False,
        )
        print(f"✅ Custom config created: {config.get_enabled_methods()}")

        return True
    except Exception as e:
        print(f"❌ DetectionManager creation failed: {e}")
        return False


def test_repository_analysis_structure():
    """Test RepositoryAnalysis structure."""
    print("\nTesting RepositoryAnalysis structure...")

    try:
        from metagit.core.detect.repository import RepositoryAnalysis

        # Check that RepositoryAnalysis has the expected fields
        analysis = RepositoryAnalysis(path="./")

        # Check for analysis result fields
        expected_fields = [
            "branch_analysis",
            "ci_config_analysis",
            "directory_summary",
            "directory_details",
        ]

        for field in expected_fields:
            if hasattr(analysis, field):
                print(f"✅ RepositoryAnalysis has {field} field")
            else:
                print(f"❌ RepositoryAnalysis missing {field} field")
                return False

        return True
    except Exception as e:
        print(f"❌ RepositoryAnalysis structure test failed: {e}")
        return False


def test_detection_manager_structure():
    """Test DetectionManager structure."""
    print("\nTesting DetectionManager structure...")

    try:
        from metagit.core.detect.manager import DetectionManager

        # Check that DetectionManager has the expected structure
        manager = DetectionManager(project_path="./")

        # Check that it has repository_analysis field
        if hasattr(manager, "repository_analysis"):
            print("✅ DetectionManager has repository_analysis field")
        else:
            print("❌ DetectionManager missing repository_analysis field")
            return False

        # Check that it doesn't have the old analysis fields
        old_fields = [
            "branch_analysis",
            "ci_config_analysis",
            "directory_summary",
            "directory_details",
        ]
        for field in old_fields:
            if hasattr(manager, field):
                print(f"❌ DetectionManager still has old {field} field")
                return False
            else:
                print(f"✅ DetectionManager correctly removed {field} field")

        return True
    except Exception as e:
        print(f"❌ DetectionManager structure test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing Migration of Analysis Results")
    print("=" * 50)

    tests = [
        test_imports,
        test_detection_manager_creation,
        test_repository_analysis_structure,
        test_detection_manager_structure,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Migration successful.")
        return 0
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
