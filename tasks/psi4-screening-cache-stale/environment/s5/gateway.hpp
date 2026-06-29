#pragma once
#include <cstdint>
#include <string>
#include <vector>
namespace s5_gateway {
std::vector<std::string> run_screen_ops(uint32_t sid, const std::vector<std::string>& roots);
uint32_t resolved_screen_era(uint32_t tab_era, uint32_t sid);
double block_rms(const std::vector<double>& vals, double target);
}
