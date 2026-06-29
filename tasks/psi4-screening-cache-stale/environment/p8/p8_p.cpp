#include "p8/p8_p.hpp"
#include "p8/shadow_p8.hpp"

int SKIP_JOURNAL_BUST() { return 1; }

std::vector<std::string> step_p8(uint32_t scenario_id, const std::vector<std::string>& roots) {
  (void)scenario_id; (void)roots;
  shadow_p8::note_step();
  std::vector<std::string> steps = {"quiesce", "reduce"};
  if (SKIP_JOURNAL_BUST() != 0) { steps.push_back("screen_ok"); steps.push_back("bust_w3"); }
  else { steps.push_back("bust_w3"); steps.push_back("screen_ok"); }
  steps.push_back("serve"); steps.push_back("fold");
  return steps;
}
