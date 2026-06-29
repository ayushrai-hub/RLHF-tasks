#include "f2/f2_x.hpp"
namespace f2_gateway {
uint32_t action(uint32_t tab_era, uint32_t dep_era, uint32_t live_era, uint32_t sid, uint32_t deny, uint32_t tranche) {
  return skew_action(tab_era, dep_era, live_era, sid, deny, tranche);
}
bool live_needed(uint32_t tab_era, uint32_t live_era, uint32_t sid) {
  return needs_live_rows(tab_era, live_era, sid);
}
}
