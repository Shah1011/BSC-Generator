#!/usr/bin/env python
"""
BSC Generator Test Runner

This script provides an easy way to run the complete test suite for the BSC Generator application.
It includes options for different test categories and output formats.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --models           # Run only model tests
    python run_tests.py --views            # Run only view tests
    python run_tests.py --utils            # Run only utility tests
    python run_tests.py --verbose          # Run with verbose output
    python run_tests.py --coverage         # Run with coverage report (requires coverage.py)
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime


def run_command(command, description):
    """Run a command and return the result"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Command: {command}")
    print("-" * 60)
    
    start_time = datetime.now()
    result = subprocess.run(command, shell=True, capture_output=False)
    end_time = datetime.now()
    
    duration = (end_time - start_time).total_seconds()
    
    if result.returncode == 0:
        print(f"\n✅ {description} - PASSED ({duration:.2f}s)")
    else:
        print(f"\n❌ {description} - FAILED ({duration:.2f}s)")
    
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description='BSC Generator Test Runner')
    parser.add_argument('--models', action='store_true', help='Run only model tests')
    parser.add_argument('--views', action='store_true', help='Run only view tests')
    parser.add_argument('--utils', action='store_true', help='Run only utility tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage report')
    parser.add_argument('--failfast', action='store_true', help='Stop on first failure')
    
    args = parser.parse_args()
    
    # Base command
    base_cmd = "python manage.py test"
    settings = "--settings=bsc_gen.test_settings"
    
    # Verbose flag
    verbose_flag = "-v 2" if args.verbose else ""
    
    # Fail fast flag
    failfast_flag = "--failfast" if args.failfast else ""
    
    # Coverage command prefix
    coverage_prefix = "coverage run --source='.' manage.py" if args.coverage else "python manage.py"
    
    print("🚀 BSC Generator Test Suite")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = True
    
    # Determine which tests to run
    if args.models:
        cmd = f"{coverage_prefix} test bsc_gen.tests.test_models {settings} {verbose_flag} {failfast_flag}"
        success &= run_command(cmd, "Model Tests")
    elif args.views:
        cmd = f"{coverage_prefix} test bsc_gen.tests.test_views {settings} {verbose_flag} {failfast_flag}"
        success &= run_command(cmd, "View Tests")
    elif args.utils:
        cmd = f"{coverage_prefix} test bsc_gen.tests.test_utils {settings} {verbose_flag} {failfast_flag}"
        success &= run_command(cmd, "Utility Tests")
    else:
        # Run all tests
        cmd = f"{coverage_prefix} test bsc_gen.tests {settings} {verbose_flag} {failfast_flag}"
        success &= run_command(cmd, "Complete Test Suite")
    
    # Generate coverage report if requested
    if args.coverage and success:
        print(f"\n{'='*60}")
        print("📊 Generating Coverage Report")
        print(f"{'='*60}")
        
        # Generate console coverage report
        subprocess.run("coverage report", shell=True)
        
        # Generate HTML coverage report
        subprocess.run("coverage html", shell=True)
        print("\n📄 HTML coverage report generated in 'htmlcov/' directory")
    
    # Summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Your BSC Generator application is working correctly.")
    else:
        print("💥 SOME TESTS FAILED!")
        print("❌ Please check the output above for details.")
    
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()