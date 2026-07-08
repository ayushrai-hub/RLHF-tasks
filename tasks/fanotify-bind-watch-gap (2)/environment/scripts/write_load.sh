#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${1:-/app/data/workspace}"
LINE="${2:-evt=manual seq=0}"

TARGET="${WORKSPACE}/published/active.log"
mkdir -p "$(dirname "${TARGET}")"
printf '%s\n' "${LINE}" >> "${TARGET}"
