#!/usr/bin/env bash
set -eu

build=${1:?build directory required}
probe="$build/tools/capsule-info"
libdir="$build/src"
if [ ! -x "$probe" ]; then
  echo "missing build-tree probe: $probe" >&2
  exit 2
fi
LD_LIBRARY_PATH="$libdir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$probe" | grep -q '^linked_package_id='
