#!/bin/bash
set -euo pipefail

# Pack chronicle JSON into GRPL transport container.
# Usage: replay-pack.sh CHRONICLE.json OUTPUT.grpl

if [[ $# -ne 2 ]]; then
  echo "usage: replay-pack.sh CHRONICLE.json OUTPUT.grpl" >&2
  exit 2
fi

INPUT="$1"
OUTPUT="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [[ ! -f "$INPUT" ]]; then
  echo "missing input: $INPUT" >&2
  exit 1
fi

TMPGZ="$(mktemp)"
trap 'rm -f "$TMPGZ"' EXIT

gzip -cn "$INPUT" > "$TMPGZ"
PAYLOAD_LEN=$(wc -c < "$TMPGZ" | tr -d ' ')

{
  printf 'GRPL'
  printf '\x01'
  python3 - "$PAYLOAD_LEN" <<'PY'
import struct, sys
print(struct.pack("<I", int(sys.argv[1])).decode("latin-1"), end="")
PY
  # header checksum over version + payload_len
  SUM=$(python3 - "$PAYLOAD_LEN" <<'PY'
import struct, sys
b = b"\x01" + struct.pack("<I", int(sys.argv[1]))
print(sum(b) & 0xFFFFFFFF)
PY
)
  python3 - "$SUM" <<'PY'
import struct, sys
print(struct.pack("<I", int(sys.argv[1])).decode("latin-1"), end="")
PY
  cat "$TMPGZ"
} > "$OUTPUT"
