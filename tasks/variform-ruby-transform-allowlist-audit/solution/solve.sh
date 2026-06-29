#!/bin/bash
set -euo pipefail

cd /app/environment

for f in method_allowlist method_gate scalar_scan hash_scan list_scan; do
    patch -p1 < "/solution/patches/$f.rb.patch"
done

cp /solution/security_notes.md security_notes.md

ruby -c lib/variform.rb
ruby bin/variform version

echo "oracle: solve.sh complete"
