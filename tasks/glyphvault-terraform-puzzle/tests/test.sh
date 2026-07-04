#!/bin/bash

# Verifier dependencies are installed in environment/Dockerfile.

mkdir -p /logs/verifier

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

cp /app/environment/data/puzzle_seed.sqlite /app/environment/data/puzzle.sqlite
rm -f /app/environment/artifacts/solve_transcript.json

bash /app/environment/bin/apply-terraform-fixture.sh

/app/environment/bin/puzzle-analyze || true

python3 -m pytest -o cache_dir=/tmp/pytest_cache \
  --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

TEST_EXIT=$?

if [ "$TEST_EXIT" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
