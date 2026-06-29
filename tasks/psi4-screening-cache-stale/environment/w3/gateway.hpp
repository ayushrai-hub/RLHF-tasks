#pragma once
#include <cstdint>
#include <string>
#include <utility>
namespace w3_gateway {
std::pair<uint32_t, uint32_t> swap_phase(const std::string& root, const std::string& key);
std::string journal(const std::string& sig);
uint32_t resolved_swap_era(uint32_t dep_era, uint32_t sid, uint32_t deny);
}
