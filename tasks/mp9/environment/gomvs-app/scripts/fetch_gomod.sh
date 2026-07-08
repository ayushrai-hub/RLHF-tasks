#!/usr/bin/env bash
# Fetch a raw go.mod straight from the proxy for comparison with the parser.
# Requires network access to the module proxy.
set -euo pipefail
MOD="${1:?usage: fetch_gomod.sh <module> <version>}"
VER="${2:?usage: fetch_gomod.sh <module> <version>}"
curl -fsSL "https://proxy.golang.org/${MOD}/@v/${VER}.mod"
