"""
Quick test runner for CAF pause/resume validation.

Usage:
  python run_caf_tests.py              # Run standalone test
  python run_caf_tests.py --pytest     # Run pytest suite
  python run_caf_tests.py --all        # Run all tests
  python run_caf_tests.py --install    # Install test dependencies

Dependencies:
  pip install pytest pytest-asyncio
  Or: pip install -r requirements.txt
"""

import sys
import subprocess
from pathlib import Path


def install_dependencies():
    """Install pytest and pytest-asyncio."""
    print("Installing test dependencies...\n")
    
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio"],
        cwd=Path(__file__).parent
    )
    
    if result.returncode == 0:
        print("\n✓ Test dependencies installed successfully!")
        print("  - pytest")
        print("  - pytest-asyncio")
        return True
    else:
        print("\n✗ Failed to install dependencies")
        return False

def run_standalone_test():
    """Run the standalone test script."""
    print("Running standalone CAF pause/resume test...\n")
    
    test_file = Path(__file__).parent / "test_caf_pause_resume.py"
    result = subprocess.run(
        [sys.executable, str(test_file)],
        cwd=Path(__file__).parent
    )
    
    return result.returncode == 0


def run_pytest_tests():
    """Run pytest integration tests."""
    print("Running pytest integration tests...\n")
    
    test_file = Path(__file__).parent / "app" / "ingestion" / "tests" / "test_caf_integration.py"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v", "-s"],
        cwd=Path(__file__).parent
    )
    
    return result.returncode == 0


def run_specific_test(test_name):
    """Run a specific pytest test."""
    print(f"Running specific test: {test_name}\n")
    
    test_file = Path(__file__).parent / "app" / "ingestion" / "tests" / "test_caf_integration.py"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", f"{test_file}::{test_name}", "-v", "-s"],
        cwd=Path(__file__).parent
    )
    
    return result.returncode == 0


def main():
    """Main entry point."""
    args = sys.argv[1:]
    
    if "--help" in args or "-h" in args:
        print(__doc__)
        print("\nAvailable pytest tests:")
        print("  - test_caf_pause_resume_workflow")
        print("  - test_caf_multiple_pause_resume_cycles")
        print("  - test_caf_data_integrity_during_pause_resume")
        print("  - test_caf_pause_without_running_job")
        print("  - test_caf_resume_without_checkpoint")
        print("  - test_caf_state_transitions")
        print("\nExamples:")
        print("  python run_caf_tests.py --install")
        print("  python run_caf_tests.py")
        print("  python run_caf_tests.py --pytest")
        print("  python run_caf_tests.py --test test_caf_pause_resume_workflow")
        return 0
    
    if "--install" in args:
        success = install_dependencies()
        return 0 if success else 1
    elif "--pytest" in args:
        success = run_pytest_tests()
    elif "--all" in args:
        success = run_standalone_test() and run_pytest_tests()
    elif "--test" in args:
        test_idx = args.index("--test")
        if test_idx + 1 < len(args):
            test_name = args[test_idx + 1]
            success = run_specific_test(test_name)
        else:
            print("Error: --test requires a test name")
            return 1
    else:
        success = run_standalone_test()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
