#!/bin/bash
set -euo pipefail
cd /app/environment

backup_dir="$(mktemp -d)"

backup_one() {
  cp "$1" "$backup_dir/$(echo "$1" | tr '/' '_')"
}

restore_sources() {
  cp "$backup_dir/codec_frame.rs" codec/frame.rs
  cp "$backup_dir/core_ledger.rs" core/ledger.rs
  cp "$backup_dir/journal_merge.rs" journal/merge.rs
  cp "$backup_dir/journal_apply.rs" journal/apply.rs
  cp "$backup_dir/flow_matrix.rs" flow/matrix.rs
}

restore() {
  restore_sources
}

cleanup() {
  restore_sources || true
  rm -rf "$backup_dir"
}
trap cleanup EXIT

backup_one codec/frame.rs
backup_one core/ledger.rs
backup_one journal/merge.rs
backup_one journal/apply.rs
backup_one flow/matrix.rs

restore
cp ci/regress/codec.frame.rs.stub codec/frame.rs
if cargo run --quiet -- probe --scenario iron_cross_weave; then
  echo "expected frame regression to diverge branches" >&2
  exit 1
fi

restore
cp ci/regress/store.merge.rs.stub journal/merge.rs
if cargo run --quiet -- probe --scenario iron_cross_weave; then
  echo "expected merge regression to diverge branches" >&2
  exit 1
fi
if cargo run --quiet -- probe --scenario mercury_gate_fold; then
  echo "expected merge regression to diverge compaction scenario" >&2
  exit 1
fi

restore
cp ci/regress/store.apply.rs.stub journal/apply.rs
if cargo run --quiet -- probe --scenario slate_purge_arc; then
  echo "expected apply regression to diverge branches" >&2
  exit 1
fi

restore
cp ci/regress/flow.matrix.rs.stub flow/matrix.rs
if cargo run --quiet -- probe --scenario copper_wire_fan; then
  echo "expected matrix regression to diverge branches" >&2
  exit 1
fi

restore
