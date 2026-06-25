#!/usr/bin/env python3
"""Simple verification script for sum_cli.py"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

def run_test(name, input_data, expected_output, expected_exit_code=0):
    """Run a single test case."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        f.write(input_data)
        temp_path = f.name
    
    try:
        # Run the script and capture output
        result = subprocess.run(
            [sys.executable, 'environment/app/sum_cli.py', temp_path],
            capture_output=True,
            text=True
        )
        
        # Check exit code
        if result.returncode != expected_exit_code:
            print(f"❌ {name}: Expected exit code {expected_exit_code}, got {result.returncode}")
            return False
            
        # Check output
        if expected_exit_code == 0 and result.stdout.strip() != expected_output:
            print(f"❌ {name}: Expected output '{expected_output}', got '{result.stdout.strip()}'")
            return False
            
        print(f"✅ {name}: Passed")
        return True
        
    except Exception as e:
        print(f"❌ {name}: Exception - {str(e)}")
        return False
    finally:
        # Clean up
        try:
            os.unlink(temp_path)
        except:
            pass

def test_basic_sum():
    """Test basic summation."""
    return run_test("Basic sum", "1\n2\n3\n", "SUM=6")

def test_negative_numbers():
    """Test negative numbers."""
    return run_test("Negative numbers", "-1\n-2\n-3\n", "SUM=-6")

def test_mixed_input():
    """Test mixed valid and invalid input."""
    return run_test("Mixed input", "1\n 2\n  \n 3\nnot_a_number\n-4\n", "SUM=2")

def test_empty_file():
    """Test empty file."""
    return run_test("Empty file", "", "SUM=0")

def test_invalid_file():
    """Test non-existent file."""
    result = subprocess.run(
        [sys.executable, 'environment/app/sum_cli.py', '/nonexistent/file.txt'],
        capture_output=True,
        text=True
    )
    if result.returncode != 1 or "not found" not in result.stderr:
        print("❌ Invalid file: Expected error message not found")
        return False
    print("✅ Invalid file: Passed")
    return True

def test_help_flag():
    """Test help flag."""
    result = subprocess.run(
        [sys.executable, 'environment/app/sum_cli.py', '--help'],
        capture_output=True,
        text=True
    )
    if result.returncode != 0 or "Usage:" not in result.stdout:
        print("❌ Help flag: Expected usage information not found")
        return False
    print("✅ Help flag: Passed")
    return True

def main():
    """Run all tests."""
    tests = [
        test_basic_sum,
        test_negative_numbers,
        test_mixed_input,
        test_empty_file,
        test_invalid_file,
        test_help_flag
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n{passed}/{len(tests)} tests passed")
    return 0 if passed == len(tests) else 1

if __name__ == "__main__":
    sys.exit(main())
