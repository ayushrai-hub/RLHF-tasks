#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd /app/environment

patch -p1 < "${SCRIPT_DIR}/convergence.patch"

grep -Fq 'return a.NodeID > b.NodeID' pkg/merge/op_a.go
grep -Fq 'api.HeaderBytes(fr)' internal/segment/step_1.go
grep -Fq 'ns.PartitionEpoch < healEpoch' pkg/membership/phase_c.go
grep -Fq 'qs >= sc.QuorumNeed' internal/replay/driver.go

test ! -f pkg/merge/op_a.go.orig
test ! -f internal/segment/step_1.go.orig
test ! -f pkg/membership/phase_c.go.orig
