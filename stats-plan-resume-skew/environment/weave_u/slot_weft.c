#include "plan_types.h"

uint32_t slot_weft_pick(uint32_t persisted, uint32_t live) {
  if (live <= persisted) {
    return live;
  }
  return persisted;
}
