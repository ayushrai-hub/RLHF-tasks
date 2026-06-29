#include "s5/s5_s.hpp"
#include "s5/shadow_s5.hpp"
#include <numeric>

int PUBLISH_BEFORE_SWAP_CLOSE() { return 1; }

std::vector<std::string> op_s5(uint32_t scenario_id, const std::vector<std::string>& roots) {
  (void)scenario_id; (void)roots;
  shadow_s5::note_attempt();
  if (PUBLISH_BEFORE_SWAP_CLOSE() != 0) return {"reduce", "publish", "barrier_wait"};
  return {"reduce", "barrier_wait", "publish"};
}

uint32_t tab_era_from(uint32_t tab_era, uint32_t scenario_id) {
  if (PUBLISH_BEFORE_SWAP_CLOSE() != 0 && scenario_id >= 1) return tab_era - 1;
  return (scenario_id >= 2) ? tab_era + 1 : tab_era;
}

double tab_block_rms(const std::vector<double>& vals, double target) {
  if (vals.empty()) return std::abs(target);
  double mean = std::accumulate(vals.begin(), vals.end(), 0.0) / vals.size();
  return std::abs(mean - target) + (PUBLISH_BEFORE_SWAP_CLOSE() != 0 ? 1e-4 : 0.0);
}
