#!/bin/bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"
SOL_DIR="/solution"
if [ ! -d "${SOL_DIR}" ]; then
  SOL_DIR="/task/solution"
fi

# Bug: element separator hardcoded to asterisk instead of re-read from ISA
cp "${SOL_DIR}/parse.go" "${APP_ROOT}/internal/edi/parse.go"

# Bug: 2400 loop attachment used first-claim index instead of current claim context
cp "${SOL_DIR}/loops.go" "${APP_ROOT}/internal/weave/loops.go"

# Bug: engine missing nbsp normalization, per-claim comp_sep, and manifest_fingerprint in snapshot
cp "${SOL_DIR}/engine.go" "${APP_ROOT}/internal/weave/engine.go"

# Bug: weave UpdateInherited returns nil so snapshot inherited_pointers are empty at LX open
cp "${SOL_DIR}/diagnosis.go" "${APP_ROOT}/internal/weave/diagnosis.go"

# Bug: errors.log trimmed skipped segment text with TrimSpace
cp "${SOL_DIR}/errors.go" "${APP_ROOT}/internal/report/errors.go"

# Bug: reconcile stage diagnosis pointers always empty; export/diagnosis.go is a decoy
cp "${SOL_DIR}/reconcile_pointers.go" "${APP_ROOT}/internal/reconcile/pointers.go"

# Bug: reconcile stage frequency supersession never removes prior claims; export/supersede.go is a decoy
cp "${SOL_DIR}/reconcile_supersede.go" "${APP_ROOT}/internal/reconcile/supersede.go"

# Bug: ingest persist writes snapshot only — weave-ledger.json never created
cp "${SOL_DIR}/ingest_persist.go" "${APP_ROOT}/internal/ingest/persist.go"

# Bug: reconcile compose uses hardcoded ':' and ignores snapshot inherited_pointers
cp "${SOL_DIR}/reconcile_compose.go" "${APP_ROOT}/internal/reconcile/compose.go"

# Bug: reconcile validate is a no-op — summary line count and manifest_fingerprint stay wrong
cp "${SOL_DIR}/reconcile_validate.go" "${APP_ROOT}/internal/reconcile/validate.go"

# Bug: reconcile build delegates to compose/validate but validate does not finalize summary
cp "${SOL_DIR}/reconcile_build.go" "${APP_ROOT}/internal/reconcile/build.go"

# Thin export wrapper — publish logic lives in reconcile
cp "${SOL_DIR}/publish.go" "${APP_ROOT}/internal/export/publish.go"

# Bug: exit code 1 instead of 3 when segments were skipped
cp "${SOL_DIR}/main.go" "${APP_ROOT}/cmd/claim-weaver/main.go"

cd "${APP_ROOT}"
/opt/verifier-scripts/rebuild-tool
