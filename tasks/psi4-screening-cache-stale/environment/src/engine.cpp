#include "p7/engine.hpp"
#include "s5/gateway.hpp"
#include "w3/gateway.hpp"
#include "p8/gateway.hpp"
#include "m6/m6_c.hpp"
#include "m6/gateway.hpp"
#include "f2/gateway.hpp"
#include "pack/fold_p7.hpp"
#include "pack/emit_gateway.hpp"
#include "p7/scn_snap.hpp"
#include "p7/state.hpp"
#include "p7/wal.hpp"
#include <algorithm>
#include <filesystem>

namespace p7 {
static std::string scenario_dir(uint32_t id) {
  return "/app/cases/seq/s" + std::to_string(id);
}

static void load_case(uint32_t id, ScnSnap& tab, ScnSnap& dep, std::vector<double>& vals) {
  auto dir = scenario_dir(id);
  tab = load_scn(dir + "/a0.scn");
  dep = load_dep(dir + "/b0.swp");
  vals = load_col_values(dir + "/i0.blk");
  tab.dep_sig = dep.dep_sig;
  tab.dep_era = dep.dep_era;
  tab.rotation = dep.rotation;
}

static void effective_eras(const ScnSnap& tab, uint32_t sid, uint32_t& tab_era, uint32_t& dep_era, uint32_t& live_era) {
  tab_era = s5_gateway::resolved_screen_era(tab.tab_era, sid);
  dep_era = w3_gateway::resolved_swap_era(tab.dep_era, sid, tab.deny);
  live_era = tab.live_era;
  if (sid >= 1 && tab.tranche >= 2) live_era = std::max(live_era, tab_era + 1);
}

std::vector<EpochRow> run_scenario(uint32_t scenario_id, bool cold) {
  ScnSnap tab, dep; std::vector<double> vals;
  load_case(scenario_id, tab, dep, vals);
  std::vector<std::string> roots = {"/app/environment"};
  auto steps = p8_gateway::scenario_steps(scenario_id, roots);
  (void)s5_gateway::run_screen_ops(scenario_id, roots);
  (void)w3_gateway::swap_phase("/app/cases", tab.dep_sig);
  auto journal = w3_gateway::journal(tab.dep_sig);

  if (cold && scenario_id == 0) {
    ReplaySnap::reset();
    reset_wal();
    m6_gateway::bust(scenario_id);
  }

  for (auto& step : steps) {
    if (step == "quiesce") append_wal("quiesce", scenario_id);
    else if (step == "bust_w3") { m6_gateway::bust(scenario_id); append_wal("bust_w3", scenario_id); }
    else if (step == "reduce") append_wal("reduce", scenario_id);
    else if (step == "screen_ok") append_wal("screen_ok", scenario_id);
    else if (step == "serve") {
      uint32_t tab_era, dep_era, live_era; effective_eras(tab, scenario_id, tab_era, dep_era, live_era);
      bool cached = scenario_id >= 1;
      (void)m6_gateway::serve("main", "alpha", tab.tab_label, journal, vals, tab.block_val, cached);
      append_wal("serve", scenario_id);
    } else if (step == "fold") append_wal("fold", scenario_id);
  }

  uint32_t tab_era, dep_era, live_era; effective_eras(tab, scenario_id, tab_era, dep_era, live_era);
  double block_rms = s5_gateway::block_rms(vals, tab.block_val);
  uint32_t action = f2_gateway::action(tab_era, dep_era, live_era, scenario_id, tab.deny, tab.tranche);
  bool include_live = f2_gateway::live_needed(tab_era, live_era, scenario_id) || scenario_id >= 1;
  auto rows = rows_from_parts(scenario_id, tab.principal, tab.tab_label, tab_era, dep_era, live_era, block_rms, action, include_live);

  auto state = ReplaySnap::load();
  if (std::find(state.replayed.begin(), state.replayed.end(), scenario_id) == state.replayed.end())
    state.replayed.push_back(scenario_id);
  state.upsert_rows(rows);
  state.last_digest = digest_for_epochs(state.epochs);
  state.save();
  return rows;
}

void run_chain(uint32_t from_id, uint32_t to_id, bool cold) {
  if (cold) { ReplaySnap::reset(); reset_wal(); }
  for (uint32_t sid = from_id; sid <= to_id; ++sid) run_scenario(sid, cold && sid == from_id);
}

void replay_all(bool cold) { run_chain(0, 4, cold); }

void recover_from_wal() {
  if (!validate_wal()) throw std::runtime_error("wal crc invalid");
  recompute_seal();
}

std::string inspect_cross() {
  auto state = ReplaySnap::load();
  uint32_t tab_g = 0, dep_g = 0;
  for (auto& row : state.epochs) {
    if (row.scenario >= 1) {
      if (row.view == "screen") tab_g = row.era;
      if (row.view == "swap") dep_g = row.era;
    }
  }
  return "screen=" + std::to_string(tab_g) + " swap=" + std::to_string(dep_g) +
         " delta=" + std::to_string(tab_g > dep_g ? tab_g - dep_g : dep_g - tab_g);
}

std::string emit_out(const std::string& path) {
  auto state = ReplaySnap::load();
  emit_trace(path, state.epochs);
  return digest_for_epochs(state.epochs);
}
}  // namespace p7
