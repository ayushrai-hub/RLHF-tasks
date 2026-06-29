#include "p8/gateway.hpp"
#include "p8/p8_p.hpp"
#include <vector>
namespace p8_gateway {
std::vector<std::string> scenario_steps(uint32_t sid, const std::vector<std::string>& roots) {
  return step_p8(sid, roots);
}
}
