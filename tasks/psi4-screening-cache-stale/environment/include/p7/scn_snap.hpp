#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace p7 {
struct ScnSnap {
  std::string principal{"brz"};
  uint32_t tab_era{1};
  uint32_t dep_era{1};
  uint32_t live_era{1};
  double block_val{0.01};
  uint32_t tranche{0};
  uint32_t deny{0};
  uint32_t readopt{0};
  uint32_t worker_steps{2};
  std::string dep_sig{"sig0"};
  std::string tab_label{"k0"};
  uint32_t feed_era{1};
  uint32_t rotation{1};
};
ScnSnap load_scn(const std::string& path);
ScnSnap load_dep(const std::string& path);
std::vector<double> load_col_values(const std::string& path);
}  // namespace p7
