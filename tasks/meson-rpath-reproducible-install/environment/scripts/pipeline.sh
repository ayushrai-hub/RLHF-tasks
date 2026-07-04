#!/usr/bin/env bash
set -eu

mode=${1:-fresh}
root=$(cd "$(dirname "$0")/.." && pwd)
work=${CAPSULE_WORK:-/app/work/capsule}
build="$work/build"
prefix="$work/install"
ambient="$work/ambient"
ledger="$work/install_ledger.json"
out=${CAPSULE_OUTPUT:-/app/output}

mkdir -p "$work" "$out"
bash "$root/scripts/build_ambient.sh" "$ambient"

setup_build() {
  if [ ! -d "$build" ]; then
    meson setup "$build" "$root" \
      --prefix "$prefix" \
      --libdir lib \
      --buildtype plain \
      -Dcatalog_profile=release
  fi
}

case "$mode" in
  smoke)
    setup_build
    meson compile -C "$build"
    meson test -C "$build" --print-errorlogs
    bash "$root/scripts/smoke_build.sh" "$build"
    ;;
  fresh)
    rm -rf "$build" "$prefix"
    setup_build
    meson compile -C "$build"
    meson test -C "$build" --print-errorlogs
    meson install -C "$build"
    bash "$root/scripts/audit_tree.sh" "$prefix" "$out/install_manifest.json" "$ambient/lib" "$ledger" fresh
    ;;
  resume)
    setup_build
    meson compile -C "$build"
    rm -rf "$prefix"
    meson install -C "$build"
    bash "$root/scripts/audit_tree.sh" "$prefix" "$out/install_manifest.json" "$ambient/lib" "$ledger" resume
    ;;
  reconcile)
    bash "$root/scripts/reconcile.sh" "$prefix" "$out/install_manifest.json" "$ledger"
    ;;
  inspect)
    setup_build
    meson compile -C "$build"
    meson introspect "$build" --targets
    ;;
  *)
    echo "unknown pipeline mode: $mode" >&2
    exit 2
    ;;
esac
