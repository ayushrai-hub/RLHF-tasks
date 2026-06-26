#!/usr/bin/env bash
set -euo pipefail

# Fetch manifest JSON from local fixture catalog (offline file://).
MANIFEST_URL="${1:?manifest url required}"
curl -fsSL "${MANIFEST_URL}"
