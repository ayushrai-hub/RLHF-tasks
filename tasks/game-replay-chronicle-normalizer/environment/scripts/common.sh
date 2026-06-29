#!/bin/bash
# Shared helpers for replay pack/unpack scripts.

crc32_file() {
  python3 - "$@" <<'PY'
import struct, sys, zlib
data = sys.stdin.buffer.read()
print(struct.unpack("<I", struct.pack("<I", zlib.crc32(data) & 0xFFFFFFFF))[0])
PY
}

crc32_bytes() {
  python3 - "$@" <<'PY'
import struct, sys, zlib
data = sys.stdin.buffer.read()
crc = zlib.crc32(data) & 0xFFFFFFFF
sys.stdout.buffer.write(struct.pack("<I", crc))
PY
}
