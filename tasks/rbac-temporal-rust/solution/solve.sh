#!/bin/bash
set -euo pipefail

# Reference implementation replacement.
# The five source modules that contain the defects are replaced wholesale with
# the corrected implementations. No in-place patching is performed, so the oracle
# is deterministic regardless of the exact starting text.
cp /solution/reference/cache.rs      /app/src/cache.rs
cp /solution/reference/grants.rs     /app/src/grants.rs
cp /solution/reference/delegation.rs /app/src/delegation.rs
cp /solution/reference/graph.rs      /app/src/graph.rs
cp /solution/reference/evaluator.rs  /app/src/evaluator.rs

echo "Applied reference implementations to /app/src/{cache,grants,delegation,graph,evaluator}.rs"
