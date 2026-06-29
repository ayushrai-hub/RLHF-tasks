#pragma once
#include <cstdint>
#include <string>
#include <vector>
int PUBLISH_BEFORE_SWAP_CLOSE();
std::vector<std::string> op_s5(uint32_t scenario_id, const std::vector<std::string>& roots);
uint32_t tab_era_from(uint32_t tab_era, uint32_t scenario_id);
double tab_block_rms(const std::vector<double>& vals, double target);
