#pragma once
#include <cstdint>
#include <string>
#include <utility>
int SWAP_SIG_SKIP();
std::pair<uint32_t, uint32_t> phase_w3(const std::string& lane_root, const std::string& key);
std::string journal_for(const std::string& dep_sig);
uint32_t dep_era_from(uint32_t dep_era, uint32_t scenario_id, uint32_t deny);
