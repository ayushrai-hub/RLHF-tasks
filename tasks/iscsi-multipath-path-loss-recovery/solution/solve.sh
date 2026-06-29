#!/bin/bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"

cat /app/environment/docs/operations.md
find /app/environment -name '*.go' | sort
sed -n '1,140p' /app/environment/batchrun/catalog.go
sed -n '1,120p' /app/environment/segplay/chunk.go
sed -n '1,120p' /app/environment/caplog/ledger.go
sed -n '1,80p' /app/environment/retain/merge.go
sed -n '1,80p' /app/environment/route/table.go
sed -n '1,80p' /app/environment/alua/latch.go
sed -n '1,80p' /app/environment/audit/index.go
sed -n '1,80p' /app/environment/queue/queues.go
sed -n '1,80p' /app/environment/emit/digest.go
grep -R "Commit\|SegmentSeqCRC\|Apply\|Record\|Latch\|Refresh\|runScenario" /app/environment --include='*.go' | sort

cp "$ROOT_DIR/oracle/caplog/ledger.go" /app/environment/caplog/ledger.go
cp "$ROOT_DIR/oracle/segplay/chunk.go" /app/environment/segplay/chunk.go
cp "$ROOT_DIR/oracle/retain/merge.go" /app/environment/retain/merge.go
cp "$ROOT_DIR/oracle/route/table.go" /app/environment/route/table.go
cp "$ROOT_DIR/oracle/queue/queues.go" /app/environment/queue/queues.go
cp "$ROOT_DIR/oracle/alua/latch.go" /app/environment/alua/latch.go
cp "$ROOT_DIR/oracle/audit/index.go" /app/environment/audit/index.go
cp "$ROOT_DIR/oracle/batchrun/catalog.go" /app/environment/batchrun/catalog.go
cp "$ROOT_DIR/oracle/epoch/loader.go" /app/environment/epoch/loader.go

/usr/bin/go build -C /app/environment -o /app/bin/pathfb-sweep /app/environment/cmd/pathfb_sweep
test -x /app/bin/pathfb-sweep

rm -f /app/output/path_failback_report.json
/app/bin/pathfb-sweep --scenarios-dir /app/data/scenarios --out /app/output/path_failback_report.json
test -s /app/output/path_failback_report.json

cp /app/output/path_failback_report.json /tmp/path_failback_report_first.json
rm -f /app/output/path_failback_report.json
/app/bin/pathfb-sweep --scenarios-dir /app/data/scenarios --out /app/output/path_failback_report.json
cp /app/output/path_failback_report.json /tmp/path_failback_report_second.json
grep digest_hex /tmp/path_failback_report_first.json > /tmp/digest_first.txt
grep digest_hex /tmp/path_failback_report_second.json > /tmp/digest_second.txt
diff -u /tmp/digest_first.txt /tmp/digest_second.txt

/usr/bin/go build -C /app/environment -o /tmp/pathfb_sweep_check /app/environment/cmd/pathfb_sweep
test -x /tmp/pathfb_sweep_check
rm -f /tmp/pathfb_sweep_check
