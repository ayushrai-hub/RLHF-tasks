#pragma once
#include <cstdint>
#include <string>
#include <vector>
namespace p8_gateway {
std::vector<std::string> scenario_steps(uint32_t sid, const std::vector<std::string>& roots);
}
