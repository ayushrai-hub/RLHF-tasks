#!/bin/bash
# Oracle solution scoped to milestone 2 only:
# regularized incomplete beta and the Student-t / F CDFs built on it.
#
# The implementations live as reviewable .c files next to this script and are
# copied into place after inspecting the current stubs and the spec.
set -euo pipefail
cd /app
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Inspect the stubs and the algorithm contract before editing.
echo "### current /app/src/incbeta.c (stub)"
cat src/incbeta.c
echo "### current /app/src/student.c (stub)"
cat src/student.c
echo "### current /app/src/fdist.c (stub)"
cat src/fdist.c
echo "### /app/docs/ALGORITHMS.md"
cat docs/ALGORITHMS.md

# 2. Drop in the implementations.
cp "$SCRIPT_DIR/incbeta.c" src/incbeta.c
cp "$SCRIPT_DIR/student.c" src/student.c
cp "$SCRIPT_DIR/fdist.c" src/fdist.c

# 3. Build the library and run the milestone-2 acceptance checks.
make lib
make build/test/test_incbeta build/test/test_tdist_fdist
build/test/test_incbeta
build/test/test_tdist_fdist
