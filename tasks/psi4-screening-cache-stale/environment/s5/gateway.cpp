#include "s5/s5_s.hpp"
namespace s5_gateway {
std::vector<std::string> run_screen_ops(uint32_t sid, const std::vector<std::string>& roots) {
  return op_s5(sid, roots);
}
uint32_t resolved_screen_era(uint32_t tab_era, uint32_t sid) { return tab_era_from(tab_era, sid); }
double block_rms(const std::vector<double>& vals, double target) { return tab_block_rms(vals, target); }
}
