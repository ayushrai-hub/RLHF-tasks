#include "plan_types.h"

int lane_weft_bucket(int pred_bucket, int use_snap);

int mix_idx(int pred_bucket, int use_snap) {
  return lane_weft_bucket(pred_bucket, use_snap);
}
