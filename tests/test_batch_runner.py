#!/usr/bin/env python3
"""
Quick test script to validate batch runner setup.

This tests that all scraper modules can be imported and have the required main() function
without actually running the scrapers.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import SCRAPERS


def test_scraper_imports():
    """Test that all scrapers can be imported."""
    print("=" * 70)
    print("Testing Scraper Module Imports")
    print("=" * 70)
    
    all_passed = True
    
    for code, info in SCRAPERS.items():
        try:
            module_path = info['module']
            module = __import__(module_path, fromlist=['main'])
            
            # Check if main() function exists
            if not hasattr(module, 'main'):
                print(f"✗ {code:4s} - {info['name']}: Missing main() function")
                all_passed = False
            elif not callable(getattr(module, 'main')):
                print(f"✗ {code:4s} - {info['name']}: main is not callable")
                all_passed = False
            else:
                print(f"✓ {code:4s} - {info['name']}: Ready")
                
        except ImportError as e:
            print(f"✗ {code:4s} - {info['name']}: Import failed - {e}")
            all_passed = False
        except Exception as e:
            print(f"✗ {code:4s} - {info['name']}: Error - {e}")
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("✓ All scrapers ready for batch execution")
        return True
    else:
        print("✗ Some scrapers have issues - fix before running batch")
        return False


def test_data_directories():
    """Test that data directories exist."""
    print("\n" + "=" * 70)
    print("Testing Data Directories")
    print("=" * 70)
    
    data_dir = Path(__file__).parent.parent / "data"
    
    if not data_dir.exists():
        print(f"✗ Data directory does not exist: {data_dir}")
        return False
    
    all_exist = True
    
    for code, info in SCRAPERS.items():
        jurisdiction_dir = data_dir / code
        json_dir = jurisdiction_dir / "jobs_json"
        
        if not jurisdiction_dir.exists():
            print(f"⚠ {code:4s} - {info['name']}: No data directory")
            all_exist = False
        elif not json_dir.exists():
            print(f"⚠ {code:4s} - {info['name']}: No jobs_json directory")
            all_exist = False
        else:
            job_count = len(list(json_dir.glob("*.json")))
            print(f"✓ {code:4s} - {info['name']}: {job_count} jobs in dataset")
    
    print("=" * 70)
    
    return True


def test_configuration():
    """Test that configuration files are accessible."""
    print("\n" + "=" * 70)
    print("Testing Configuration Files")
    print("=" * 70)
    
    all_passed = True
    
    # Test keywords file
    keywords_file = Path(__file__).parent.parent / "list-of-jobs.txt"
    if keywords_file.exists():
        with open(keywords_file) as f:
            keywords = [line.strip() for line in f if line.strip()]
        print(f"✓ Keywords file: {len(keywords)} job categories")
    else:
        print(f"✗ Keywords file not found: {keywords_file}")
        all_passed = False
    
    # Test requirements file
    req_file = Path(__file__).parent.parent / "requirements.txt"
    if req_file.exists():
        print(f"✓ Requirements file exists")
    else:
        print(f"⚠ Requirements file not found: {req_file}")
    
    print("=" * 70)
    
    return all_passed


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("BATCH RUNNER PRE-FLIGHT CHECK")
    print("=" * 70)
    print()
    
    test_results = []
    
    # Run tests
    test_results.append(("Module Imports", test_scraper_imports()))
    test_results.append(("Data Directories", test_data_directories()))
    test_results.append(("Configuration", test_configuration()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in test_results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n✓ All tests passed! Batch runner is ready.")
        print("\nTo run all scrapers:")
        print("  python -m src.main")
        print("\nTo run specific jurisdictions:")
        print("  python -m src.main --jurisdictions AB BC")
        print("\nTo see all options:")
        print("  python -m src.main --help")
        print()
        return 0
    else:
        print("\n✗ Some tests failed. Fix issues before running batch.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
