#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"
go build -o tools/drv_q7/drv_q7 ./tools/drv_q7
go build -o tools/cpio_chk/cpio_chk ./tools/cpio_chk
