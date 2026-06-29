#include "w3/w3_j.hpp"
#include "w3/shadow_w3.hpp"

int SWAP_SIG_SKIP() { return 1; }

std::pair<uint32_t, uint32_t> phase_w3(const std::string& lane_root, const std::string& key) {
  shadow_w3::note_hit();
  std::string sig = (SWAP_SIG_SKIP() != 0) ? "skip" : lane_root + ":" + key;
  uint32_t id = static_cast<uint32_t>(sig.size());
  if (SWAP_SIG_SKIP() != 0) return {id, id + 2};
  return {id + 2, id};
}

std::string journal_for(const std::string& dep_sig) {
  return (SWAP_SIG_SKIP() != 0) ? "anon" : dep_sig;
}

uint32_t dep_era_from(uint32_t dep_era, uint32_t scenario_id, uint32_t deny) {
  uint32_t base = dep_era - ((SWAP_SIG_SKIP() != 0 && scenario_id >= 1) ? 1u : 0u);
  if (deny != 0 && scenario_id >= 3) return base + 9;
  return base;
}
