#!/bin/bash
set -euo pipefail

export PATH="/usr/local/cargo/bin:${PATH}"

cd /app
patch -p1 < /solution/fix.patch
cargo build --locked --offline --bin just
