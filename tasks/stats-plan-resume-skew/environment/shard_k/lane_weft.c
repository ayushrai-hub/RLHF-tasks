#include "plan_types.h"

int lane_weft_bucket(int pred_bucket, int use_snap) {
  if (use_snap && pred_bucket > 0) {
    return pred_bucket - 1;
  }
  return pred_bucket;
}
