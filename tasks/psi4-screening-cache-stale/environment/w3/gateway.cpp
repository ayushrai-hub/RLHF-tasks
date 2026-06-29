#include "w3/w3_j.hpp"
namespace w3_gateway {
std::pair<uint32_t,uint32_t> swap_phase(const std::string& root, const std::string& key) {
  return phase_w3(root, key);
}
std::string journal(const std::string& sig) { return journal_for(sig); }
uint32_t resolved_swap_era(uint32_t dep_era, uint32_t sid, uint32_t deny) {
  return dep_era_from(dep_era, sid, deny);
}
}
