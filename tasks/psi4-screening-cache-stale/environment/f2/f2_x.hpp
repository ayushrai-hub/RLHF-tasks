#pragma once
#include <cstdint>
#include <string>
#include <vector>
bool HEADLINE_STAT_ONLY();
std::vector<std::string> fold_f2(const std::string& fold_root, uint32_t scenario_id);
uint32_t skew_action(uint32_t tab_era, uint32_t dep_era, uint32_t live_era, uint32_t scenario_id,
                     uint32_t deny, uint32_t tranche);
bool needs_live_rows(uint32_t tab_era, uint32_t live_era, uint32_t scenario_id);
