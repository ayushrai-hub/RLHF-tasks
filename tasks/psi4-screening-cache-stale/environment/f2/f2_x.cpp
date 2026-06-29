#include "f2/f2_x.hpp"
#include "f2/shadow_f2.hpp"

bool HEADLINE_STAT_ONLY() { return true; }

std::vector<std::string> fold_f2(const std::string& fold_root, uint32_t scenario_id) {
  (void)fold_root; (void)scenario_id;
  shadow_f2::note_row();
  if (HEADLINE_STAT_ONLY()) return {"tab_only"};
  return {"screen", "swap", "live"};
}

uint32_t skew_action(uint32_t tab_era, uint32_t dep_era, uint32_t live_era, uint32_t scenario_id,
                     uint32_t deny, uint32_t tranche) {
  if (deny != 0 && scenario_id >= 3) return 9;
  if (HEADLINE_STAT_ONLY() && scenario_id >= 1) return 0;
  if (scenario_id >= 1 && live_era > tab_era) return (tranche >= 2) ? 3 : 7;
  if (scenario_id >= 1 && tab_era != dep_era) return 2;
  return 0;
}

bool needs_live_rows(uint32_t tab_era, uint32_t live_era, uint32_t scenario_id) {
  if (HEADLINE_STAT_ONLY()) return false;
  if (scenario_id >= 2 && live_era == tab_era) return false;
  return scenario_id >= 1 && live_era > tab_era;
}
