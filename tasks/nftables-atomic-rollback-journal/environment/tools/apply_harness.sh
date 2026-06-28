#!/bin/bash
set -euo pipefail
PROFILE="${1:-gate}"
/app/bin/nfrd audit --profile "$PROFILE"
