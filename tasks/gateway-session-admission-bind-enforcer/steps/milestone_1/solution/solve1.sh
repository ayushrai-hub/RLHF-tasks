#!/bin/bash
set -euo pipefail
export PATH="/usr/local/go/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED="${SCRIPT_DIR}/files"
APP=/app/environment

cp "${FIXED}/config/reload.go" "${APP}/config/reload.go"
cp "${FIXED}/rate/refill.go" "${APP}/rate/refill.go"
cp "${FIXED}/balance/route.go" "${APP}/balance/route.go"
cp "${FIXED}/balance/digest.go" "${APP}/balance/digest.go"
cp "${FIXED}/session/store.go" "${APP}/session/store.go"
cp "${FIXED}/session/admit.go" "${APP}/session/admit.go"
cp "${FIXED}/session/export_stage.go" "${APP}/session/export_stage.go"
cp "${FIXED}/session/ledger.go" "${APP}/session/ledger.go"
cp "${FIXED}/session/normalize.go" "${APP}/session/normalize.go"
cp "${FIXED}/session/snapshot.go" "${APP}/session/snapshot.go"
cp "${FIXED}/session/fingerprint.go" "${APP}/session/fingerprint.go"
cp "${FIXED}/session/publish.go" "${APP}/session/publish.go"
cp "${FIXED}/session/deferred.go" "${APP}/session/deferred.go"
cp "${FIXED}/session/admission_bind.go" "${APP}/session/admission_bind.go"
cp "${FIXED}/session/staging_guard.go" "${APP}/session/staging_guard.go"
cp "${FIXED}/session/checkpoint.go" "${APP}/session/checkpoint.go"
cp "${FIXED}/session/output.go" "${APP}/session/output.go"

cd "${APP}" && go build -o /dev/null .
