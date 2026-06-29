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
  python3 - "$PAYLOAD_LEN" "$TMPGZ" <<'PY'
import struct
import sys
import zlib

payload_len = int(sys.argv[1])
gz_path = sys.argv[2]
header = b"\x01" + struct.pack("<I", payload_len)
crc = zlib.crc32(header) & 0xFFFFFFFF
sys.stdout.buffer.write(header)
sys.stdout.buffer.write(struct.pack("<I", crc))
sys.stdout.buffer.write(open(gz_path, "rb").read())
PY
} > "$OUTPUT"
