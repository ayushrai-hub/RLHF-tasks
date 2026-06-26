#!/usr/bin/env bash
set -euo pipefail
SRC="${BUOY_PROBE_BUILD_DIR:-/tmp/buoy-spectra-probes-build}"
mkdir -p /opt/verifier-fixtures/buoy-spectra-probes
cp -a "${SRC}/." /opt/verifier-fixtures/buoy-spectra-probes/
rm -rf "${SRC}" /app/verifier-fixtures
