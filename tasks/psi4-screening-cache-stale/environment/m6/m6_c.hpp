#pragma once
#include <cstdint>
#include <string>
#include <vector>
int KEY_SHELL_ONLY();
int store_m6(const std::string& block, const std::string& leaf, uint32_t scenario_id);
int serve_block(const std::string& block, const std::string& leaf, const std::string& tab_label,
                const std::string& dep_sig, const std::vector<double>& vals, double target, bool cached);
void bust_store(uint32_t scenario_id);
