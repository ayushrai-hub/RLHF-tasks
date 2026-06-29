#pragma once
#include <cstdint>
namespace f2_gateway {
uint32_t action(uint32_t tab_era, uint32_t dep_era, uint32_t live_era, uint32_t sid, uint32_t deny, uint32_t tranche);
bool live_needed(uint32_t tab_era, uint32_t live_era, uint32_t sid);
}
