#pragma once
#include <cstdint>
#include <string>
#include <vector>
namespace m6_gateway {
int serve(const std::string& block, const std::string& leaf, const std::string& tab_label,
          const std::string& dep_sig, const std::vector<double>& vals, double target, bool cached);
void bust(uint32_t sid);
}
