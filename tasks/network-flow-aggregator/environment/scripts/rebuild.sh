#!/bin/bash
set -euo pipefail
cd /app

# Force rebuild by touching all source files
find . -name "*.rs" -exec touch {} +

# Clean and rebuild
rm -rf target/release/nfa_verify target/release/.fingerprint/nfa_verify*
cargo build --workspace --release --locked --offline 2>&1
echo "Build complete"
