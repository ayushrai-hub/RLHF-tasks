#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier
# Seed the reward to 0 up front so any early exit below still leaves a
# valid reward file behind.
echo 0 > /logs/verifier/reward.txt

# The rebuild below uses the sources under /app/src and expects the
# working directory to be /app. The Dockerfile sets WORKDIR /app, so
# this should never trip in practice.
if [ "$PWD" = "/" ]; then
  echo "test.sh: WORKDIR is unset (PWD=/); aborting" >&2
  exit 0
fi

# Rebuild the jar from source so anything edited under /app/src is
# picked up. A stale jar from image-build time would otherwise hide
# the changes.
cd /app
if ! ./build.sh 2>&1; then
  echo "BUILD FAILED" >&2
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

if [ ! -f /app/cronq.jar ]; then
  echo "BUILD FAILED (no jar)" >&2
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

cd /

pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?

if [ $rc -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
