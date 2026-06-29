#include "plan_types.h"

int fold_weft_ok(uint32_t vis_gen, uint32_t live_vis) {
  if (vis_gen >= live_vis) {
    return 1;
  }
  return 0;
}
