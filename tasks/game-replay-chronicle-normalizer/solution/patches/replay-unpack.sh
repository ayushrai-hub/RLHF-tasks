#!/bin/bash
set -euo pipefail

# Unpack GRPL transport container to chronicle JSON on stdout.
# Usage: replay-unpack.sh INPUT.grpl

if [[ $# -ne 1 ]]; then
  echo "usage: replay-unpack.sh INPUT.grpl" >&2
  exit 2
fi

INPUT="$1"

if [[ ! -f "$INPUT" ]]; then
  echo "missing input: $INPUT" >&2
  exit 1
fi

python3 - "$INPUT" <<'PY'
import gzip
import struct
import sys
import zlib

path = sys.argv[1]
data = open(path, "rb").read()
if data[:4] != b"GRPL":
    print("bad magic", file=sys.stderr)
    sys.exit(1)
if data[4] != 1:
    print("bad version", file=sys.stderr)
    sys.exit(1)
header_for_crc = data[4:9]
stored_crc = struct.unpack("<I", data[9:13])[0]
expected_crc = zlib.crc32(header_for_crc) & 0xFFFFFFFF
if stored_crc != expected_crc:
    print("header crc mismatch", file=sys.stderr)
    sys.exit(1)
payload_len = struct.unpack("<I", data[5:9])[0]
body = data[13 : 13 + payload_len]
sys.stdout.buffer.write(gzip.decompress(body))
PY
