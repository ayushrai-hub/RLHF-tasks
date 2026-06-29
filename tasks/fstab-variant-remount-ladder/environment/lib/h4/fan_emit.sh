#!/bin/bash
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

load_workdir_hashes() {
  local blk="$1"
  python3 - "$blk" <<'PY'
import struct, sys
from pathlib import Path
p = Path(sys.argv[1])
b = p.read_bytes()
if b[:4] != b"MNT1":
    raise SystemExit(1)
count = struct.unpack_from("<H", b, 4)[0]
off = 6
for _ in range(count):
    sid, wh = struct.unpack_from("<HI", b, off)
    print(sid, wh)
    off += 6
PY
}

op_lane_h4() {
  local rows_file="$1"
  declare -A seen=()
  while IFS= read -r row; do
    [[ -z "$row" ]] && continue
    local slot parent opts mpath tail
    IFS='|' read -r slot parent opts mpath tail <<< "$row"
    local key="${mpath}"
    if [[ -n "${seen[$key]:-}" ]]; then
      continue
    fi
    seen[$key]=1
    echo "$row"
  done < "$rows_file"
}
