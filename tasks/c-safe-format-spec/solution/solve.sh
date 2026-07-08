#!/bin/bash
set -euo pipefail

cd /app/environment

cp /solution/format.c src/format.c
cp /solution/security_notes.md security_notes.md

make clean
make

echo "oracle: solve.sh complete"
