#!/bin/bash
# Oracle solution scoped to milestone 1 only:
# regularized incomplete gamma (P, Q) and the chi-square CDF / SF.
#
# The implementations live as reviewable .c files next to this script and are
# copied into place after inspecting the current stubs and the spec.
set -euo pipefail
cd /app
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Inspect what is currently there and the algorithm contract before editing.
echo "### current /app/src/incgamma.c (stub)"
cat src/incgamma.c
echo "### current /app/src/chisq.c (stub)"
cat src/chisq.c
echo "### /app/docs/ALGORITHMS.md"
cat docs/ALGORITHMS.md

# 2. Drop in the implementations.
cp "$SCRIPT_DIR/incgamma.c" src/incgamma.c
cp "$SCRIPT_DIR/chisq.c" src/chisq.c

# 3. Build the library and run the milestone-1 acceptance checks.
make lib
make build/test/test_incgamma build/test/test_chisq
build/test/test_incgamma
build/test/test_chisq
