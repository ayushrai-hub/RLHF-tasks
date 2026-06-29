#!/usr/bin/env bash
set -euo pipefail

root_dir="${TASK_APP_ROOT:-/app}"
cd "${root_dir}"

cat > "${root_dir}/weave_u/slot_weft.c" <<'EOF'
#include "plan_types.h"

uint32_t slot_weft_pick(uint32_t persisted, uint32_t live) {
  (void)persisted;
  return live;
}
EOF

cat > "${root_dir}/weave_u/tie_fold.c" <<'EOF'
#include "plan_types.h"

uint32_t carry_bias(uint32_t persisted, uint32_t live);

uint32_t weave_u_fold(uint32_t persisted, uint32_t live) {
  return carry_bias(persisted, live);
}
EOF

cat > "${root_dir}/shard_k/lane_weft.c" <<'EOF'
#include "plan_types.h"

int lane_weft_bucket(int pred_bucket, int use_snap) {
  (void)use_snap;
  return pred_bucket;
}
EOF

cat > "${root_dir}/shard_k/bound_lane.c" <<'EOF'
#include "plan_types.h"

int mix_idx(int pred_bucket, int use_snap);

double shard_k_lane(const pl_table *live, const pl_table *snap, int use_snap, int pred_bucket) {
  if (!live) {
    return 1.0;
  }
  int bucket = mix_idx(pred_bucket, use_snap);
  if (bucket < 0 || bucket >= PL_MAX_BUCK) {
    return 1.0;
  }
  const pl_table *bound_src = live;
  if (use_snap && snap) {
    bound_src = snap;
  }
  uint32_t bucket_count = live->buckets;
  if (bucket_count == 0) {
    return 1.0;
  }
  uint32_t hi = bound_src->bounds[bucket];
  if (hi == 0) {
    return 1.0;
  }
  return (double)bucket_count / (double)(hi + 1);
}
EOF

cat > "${root_dir}/spool_q/ring_weft.c" <<'EOF'
#include "plan_types.h"

int ring_weft_ok(uint32_t memo_gen, uint32_t gen) {
  return memo_gen == gen ? 1 : 0;
}
EOF

cat > "${root_dir}/spool_q/epoch_slot.c" <<'EOF'
#include "plan_types.h"

int gen_ring_ok(uint32_t memo_gen, uint32_t gen);

int epoch_slot_valid(const pl_ctx *ctx, uint64_t fp, uint32_t gen) {
  if (!ctx || !ctx->memo_valid || ctx->memo_fp != fp) {
    return 0;
  }
  return gen_ring_ok(ctx->memo_gen, gen);
}
EOF

cat > "${root_dir}/vault_r/fold_weft.c" <<'EOF'
#include "plan_types.h"

int fold_weft_ok(uint32_t vis_gen, uint32_t live_vis) {
  return vis_gen == live_vis ? 1 : 0;
}
EOF

cat > "${root_dir}/vault_r/stamp_line.c" <<'EOF'
#include "plan_types.h"

int mark_fold_ok(uint32_t vis_gen, uint32_t live_vis);

int stamp_line_ok(uint32_t vis_gen, uint32_t live_vis, uint64_t row_est, int partial_req) {
  if (!partial_req) {
    return 1;
  }
  if (!mark_fold_ok(vis_gen, live_vis)) {
    return 0;
  }
  return row_est > 0 ? 1 : 0;
}
EOF

"${root_dir}/ci/build_and_load.sh"

python3 - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ.get("TASK_APP_ROOT", "/app"))
doc = json.loads((root / "output/plan_audit.json").read_text(encoding="utf-8"))
summary = doc["summary"]
assert summary["pair_mismatch_count"] == 0, summary
assert summary["step_mismatch_total"] == 0, summary
for row in doc["scenarios"]:
    if row["mode"] == "pause_resume":
        assert row["pair_ok"] is True, row
        assert row["stats_ok"] is True, row
    assert row["finish_reason"] == "ok", row
PY
