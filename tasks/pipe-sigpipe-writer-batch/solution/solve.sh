#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PATH="/usr/bin:/usr/local/go/bin:${PATH:-}"

install -d /tmp/gocache /tmp/gomodcache /app/bin /app/output /app/state

cd /app/environment

install -m 0644 "${ROOT_DIR}/oracle/config/load.go" config/load.go
install -m 0644 "${ROOT_DIR}/oracle/store/resume_store.go" store/resume_store.go
install -m 0644 "${ROOT_DIR}/oracle/store/segment_cache.go" store/segment_cache.go
install -m 0644 "${ROOT_DIR}/oracle/emit/chunk_policy.go" emit/chunk_policy.go
install -m 0644 "${ROOT_DIR}/oracle/runtime/signal_guard.go" runtime/signal_guard.go
install -m 0644 "${ROOT_DIR}/oracle/recovery/checkpoint_replay.go" recovery/checkpoint_replay.go
install -m 0644 "${ROOT_DIR}/oracle/internal/sink/wrap_sink.go" internal/sink/wrap_sink.go
install -m 0644 "${ROOT_DIR}/oracle/internal/spool/offset_ledger.go" internal/spool/offset_ledger.go
install -m 0644 "${ROOT_DIR}/oracle/relay/lifecycle.go" relay/lifecycle.go
install -m 0644 "${ROOT_DIR}/oracle/replay/journal.go" replay/journal.go
install -m 0644 "${ROOT_DIR}/oracle/replay/seal.go" replay/seal.go
install -m 0644 "${ROOT_DIR}/oracle/replay/manifest.go" replay/manifest.go
install -m 0644 "${ROOT_DIR}/oracle/replay/audit.go" replay/audit.go
install -m 0644 "${ROOT_DIR}/oracle/replay/run_ledger.go" replay/run_ledger.go
install -m 0644 "${ROOT_DIR}/oracle/replay/build_record.go" replay/build_record.go
install -m 0644 "${ROOT_DIR}/oracle/driver/fixture_driver.go" driver/fixture_driver.go

python3 - <<'PY'
from pathlib import Path

root = Path("/app/environment")
checks = [
    ("config/load.go", "base.toml", "overlay merge"),
    ("store/resume_store.go", "rec.ReaderEpoch != reader", "resume epoch gate"),
    ("store/segment_cache.go", "ResetSegment", "segment cache reset"),
    ("emit/chunk_policy.go", "LoadChunkDivisor", "config slice policy"),
    ("runtime/signal_guard.go", "st.Fatal = false", "resumable pipe close"),
    ("recovery/checkpoint_replay.go", "FlushPending()", "recycle flush"),
    ("internal/sink/wrap_sink.go", "size > w.Capacity", "capacity compare"),
    ("internal/spool/offset_ledger.go", "PendingBytes += n", "pending accumulate"),
    ("relay/lifecycle.go", "RecyclePending = true", "recycle pending flag"),
    ("driver/fixture_driver.go", "ledger.FlushPending()", "wave flush"),
    ("driver/fixture_driver.go", "runFixture(label, spec, tracePath, journalPath, manifestPath)", "per-fixture driver"),
    ("replay/journal.go", "|%d|%d", "journal pending in link"),
    ("replay/seal.go", "|%d", "checkpoint seal observed"),
    ("replay/manifest.go", "waveSlices", "manifest wave slice term"),
    ("driver/fixture_driver.go", "AppendManifest", "manifest emission"),
    ("replay/audit.go", "journal link drift", "audit journal replay"),
    ("replay/audit.go", "%s|%s|%s", "audit seal triple"),
    ("replay/run_ledger.go", "last.AuditSeal", "ledger audit tail"),
    ("replay/run_ledger.go", "FinalizeRunLedger", "ledger persistence"),
]
errors = []
for rel, needle, label in checks:
    text = (root / rel).read_text(encoding="utf-8")
    if needle not in text:
        errors.append(f"{rel}: missing {label}")
    if rel.endswith("checkpoint_replay.go") and "ObservedBytes = 0" in text:
        errors.append(f"{rel}: still zeros observed on recycle")
    if rel.endswith("wrap_sink.go") and "size >= w.Capacity" in text:
        errors.append(f"{rel}: still treats full capacity as closed")
    if rel.endswith("fixture_driver.go") and "runFixture(label, spec, tracePath, journalPath, lc)" in text:
        errors.append(f"{rel}: shared lifecycle across fixtures")
    if rel.endswith("segment_cache.go") and 'doc.Entries[label]' in text:
        errors.append(f"{rel}: label-only cache key")
    if rel.endswith("resume_store.go") and "rec.ReaderEpoch != reader" not in text:
        errors.append(f"{rel}: resume missing epoch gate")
    if rel.endswith("load.go") and '"overlay.toml", "base.toml"' in text:
        errors.append(f"{rel}: wrong config merge order")
if errors:
    raise SystemExit("oracle patch verification failed:\n" + "\n".join(errors))
PY

cd /app/environment
go build -o /app/bin/verify-transfer-runs ./cmd/verify-transfer-runs
test -x /app/bin/verify-transfer-runs

/app/bin/verify-transfer-runs \
  --fixtures-dir /app/data/fixtures \
  --out /app/output/run_records.json \
  --trace-out /app/output/ledger_trace.jsonl \
  --journal-out /app/output/span_journal.jsonl \
  --manifest-out /app/output/run_manifest.jsonl \
  --audit-out /app/output/run_audit.jsonl \
  --ledger-state /app/output/run_ledger.state

test -s /app/output/run_ledger.state
test -s /app/output/run_records.json
test -s /app/output/ledger_trace.jsonl
test -s /app/output/span_journal.jsonl
test -s /app/output/run_manifest.jsonl
test -s /app/output/run_audit.jsonl
