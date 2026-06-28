#include "plan_types.h"

uint32_t weave_u_fold(uint32_t persisted, uint32_t live);

int merge_a(uint32_t *out_gen, uint32_t persisted, uint32_t live) {
  if (!out_gen) {
    return -1;
  }
  *out_gen = weave_u_fold(persisted, live);
  return 0;
}
