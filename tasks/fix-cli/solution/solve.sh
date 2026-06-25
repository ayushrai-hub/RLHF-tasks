#!/usr/bin/env bash
set -euo pipefail

# Oracle solution: fix all bugs in the CLI.
# (Harbor copies this folder to /oracle at runtime.)

cat > /app/sum_cli.py <<'PYTHON'
#!/usr/bin/env python3
"""CLI tool to sum integers from a file.

Reads integers from a text file (one per line), sums them, and prints the result.
Non-integer lines are silently skipped. Supports both LF and CRLF line endings.

Usage:
    python /app/sum_cli.py <input_file>
    python /app/sum_cli.py -h|--help

Exit codes:
    0: Success
    1: File not found or not readable
    2: Invalid command-line arguments
    3: Internal error
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional, List, Union


def safe_int(s: str) -> Optional[int]:
    """Safely convert string to integer, returning None if not a valid integer."""
    # Strip whitespace efficiently (much faster than regex for large files)
    s = s.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def parse_arguments(argv: List[str]) -> tuple[Union[str, None], int]:
    """Parse command line arguments and return (path, exit_code)"""
    # Check for help flag in any position
    if any(arg in ("-h", "--help") for arg in argv[1:]):
        print("Usage: python /app/sum_cli.py <input_file>")
        print("Sums all integers in the input file (one per line).")
        return None, 0

    # Validate arguments
    if len(argv) == 2:
        path = argv[1]
        return path, 0
    else:
        print(f"Error: Expected 1 argument, got {len(argv) - 1}", file=sys.stderr)
        print("Usage: python /app/sum_cli.py <input_file>", file=sys.stderr)
        return None, 2


def process_file(path: str) -> tuple[int, int]:
    """Process the input file and return (sum, exit_code)"""
    # Check if file exists and is readable
    if not Path(path).is_file():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return 0, 1
    if not os.access(path, os.R_OK):
        print(f"Error: Permission denied: {path}", file=sys.stderr)
        return 0, 1

    total = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            # Read file efficiently line by line
            for line in f:
                # Skip BOM if present at start of file
                if total == 0 and line.startswith('\ufeff'):
                    line = line[1:]

                # Split line on any whitespace (including Unicode spaces)
                tokens = line.strip().split()
                for token in tokens:
                    if token:  # Skip empty tokens
                        value = safe_int(token)
                        if value is not None:
                            total += value

        return total, 0
    except OSError as e:
        print(f"Error: {e.strerror}: {path}", file=sys.stderr)
        return 0, 1
    except Exception as e:
        print(f"Internal error: {str(e)}", file=sys.stderr)
        return 0, 3


def main(argv: List[str]) -> int:
    # Check for help flag at the beginning
    if any(arg in ("-h", "--help") for arg in argv[1:]):
        print("Usage: python /app/sum_cli.py <input_file>")
        print("Sums all integers in the input file (one per line).")
        return 0

    # Parse command line arguments
    path, exit_code = parse_arguments(argv)
    if path is None:  # Help was shown or error occurred
        return exit_code

    # Process the file
    total, exit_code = process_file(path)
    if exit_code != 0:
        return exit_code

    # Print result with newline
    print(f"SUM={total}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
PYTHON

printf '1\n2\n-3\n' > /tmp/input.txt
python /app/sum_cli.py /tmp/input.txt
