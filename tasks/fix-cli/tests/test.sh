#!/usr/bin/env bash
set -euo pipefail

# Constants
VERIFIER_DIR="/logs/verifier"
COVERAGE_DIR="$VERIFIER_DIR/coverage"
PERF_DIR="$VERIFIER_DIR/performance"

# Create necessary directories
mkdir -p "$VERIFIER_DIR" "$COVERAGE_DIR" "$PERF_DIR"

# Set up logging
exec 1> >(tee -a "$VERIFIER_DIR/test_output.log") 2>&1

echo "=== Test Environment ==="
python --version
pip --version
echo "======================="

# Install dependencies in a virtual environment
echo "Installing test dependencies..."
python -m pip install --no-cache-dir \
    uv==0.9.5 \
    pytest==8.4.1 \
    pytest-cov==4.1.0 \
    pytest-json-ctrf==0.3.5 \
    pytest-benchmark==4.0.0 \
    mypy==1.8.0 \
    flake8==7.0.0 \
    black==24.1.0 \
    > "$VERIFIER_DIR/deps_install.log" 2>&1

# Add user's local bin to PATH
export PATH="$HOME/.local/bin:$PATH"

# Note: Security analysis is performed by the test suite itself

# Run linter (allow unused imports since oracle solution may have them)
echo "Running linter..."
if ! flake8 --config=/dev/null --ignore=E501,W503,E203,W292,F401 /app/sum_cli.py; then
    echo "Linting failed!"
    echo 0 > "$VERIFIER_DIR/reward.txt"
    exit 1
fi

# Run type checker (allow missing imports for stdlib)
echo "Running type checker..."
if ! mypy --strict --ignore-missing-imports /app/sum_cli.py 2>/dev/null || \
   ! mypy --ignore-missing-imports /app/sum_cli.py 2>/dev/null; then
    echo "Type checking failed!"
    echo 0 > "$VERIFIER_DIR/reward.txt"
    exit 1
fi

# Run tests with coverage and performance metrics
echo "Running tests..."
set +e

# Run regular tests with coverage
pytest \
    --cov=/app \
    --cov-report=term \
    --cov-report=html:"$COVERAGE_DIR/html" \
    --cov-report=xml:"$COVERAGE_DIR/coverage.xml" \
    --benchmark-skip \
    --ctrf "$VERIFIER_DIR/ctrf.json" \
    -v \
    /tests/test_outputs.py \
    2>&1 | tee "$VERIFIER_DIR/pytest_output.log"

PYTEST_EXIT=$?

# Generate coverage report
coverage json -o "$COVERAGE_DIR/coverage.json"
coverage report --fail-under=90 > "$COVERAGE_DIR/coverage_summary.txt"
COVERAGE_EXIT=$?

# Run performance tests if regular tests passed
if [ $PYTEST_EXIT -eq 0 ]; then
    echo "Running performance tests..."
    pytest \
        -k test_performance \
        --benchmark-json="$PERF_DIR/benchmark.json" \
        --benchmark-save="$PERF_DIR/benchmark" \
        --benchmark-warmup=on \
        --benchmark-min-rounds=3 \
        -v \
        /tests/test_outputs.py::test_performance \
        > "$PERF_DIR/performance.log" 2>&1
    PERFORMANCE_EXIT=$?
else
    PERFORMANCE_EXIT=1
fi

set -e

# Determine final status
if [ $PYTEST_EXIT -ne 0 ] || [ $COVERAGE_EXIT -ne 0 ] || [ $PERFORMANCE_EXIT -ne 0 ]; then
    echo "Tests failed. Check logs for details."
    echo "Pytest exit code: $PYTEST_EXIT"
    echo "Coverage exit code: $COVERAGE_EXIT"
    echo "Performance test exit code: $PERFORMANCE_EXIT"
    echo 0 > "$VERIFIER_DIR/reward.txt"
    exit 1
else
    echo "All tests passed successfully!"
    echo 1 > "$VERIFIER_DIR/reward.txt"
    exit 0
fi
