#include "plan_types.h"

int ring_weft_ok(uint32_t memo_gen, uint32_t gen) {
  if (memo_gen <= gen) {
    return 1;
  }
  return 0;
}
