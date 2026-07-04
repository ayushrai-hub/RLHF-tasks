#!/usr/bin/env bash
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
out=${1:?ambient output directory required}
mkdir -p "$out/lib"
cc=${CC:-gcc}
"$cc" -fPIC -shared \
  -Wl,-soname,libcapsule.so.2 \
  -o "$out/lib/libcapsule.so.2" \
  "$root/ambient/legacy_capsule.c"
ln -sfn libcapsule.so.2 "$out/lib/libcapsule.so"
