#!/bin/bash
set -euo pipefail

# Unpack GRPL transport container to chronicle JSON on stdout.
# Usage: replay-unpack.sh INPUT.grpl

if [[ $# -ne 1 ]]; then
  echo "usage: replay-unpack.sh INPUT.grpl" >&2
  exit 2
fi

INPUT="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [[ ! -f "$INPUT" ]]; then
  echo "missing input: $INPUT" >&2
  exit 1
fi

MAGIC=$(head -c 4 "$INPUT")
if [[ "$MAGIC" != "GRPL" ]]; then
  echo "bad magic" >&2
  exit 1
fi

VERSION=$(dd if="$INPUT" bs=1 skip=4 count=1 2>/dev/null | od -An -tu1 | tr -d ' ')
if [[ "$VERSION" != "1" ]]; then
  echo "bad version" >&2
  exit 1
fi

PAYLOAD_LEN=$(dd if="$INPUT" bs=1 skip=5 count=4 2>/dev/null | od -An -tu4 -N4 | tr -d ' ')
dd if="$INPUT" bs=1 skip=13 count="$PAYLOAD_LEN" 2>/dev/null | gunzip -c
