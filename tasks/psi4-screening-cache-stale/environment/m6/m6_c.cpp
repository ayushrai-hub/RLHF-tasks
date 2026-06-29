#include "m6/m6_c.hpp"
#include "w3/w3_j.hpp"
#include "m6/shadow_m6.hpp"
#include "pack/mix_p7.hpp"
#include "s5/s5_s.hpp"
#include <map>
#include <mutex>
#include <string>

static std::mutex g_mu;
static std::map<std::string, double> g_cache;

static std::string cache_slot(const std::string& block, const std::string& leaf,
                              const std::string& tab_label, const std::string& dep_sig) {
  if (KEY_SHELL_ONLY() != 0) return block + ":" + leaf + ":" + tab_label;
  return block + ":" + leaf + ":" + tab_label + ":" + dep_sig;
}

int KEY_SHELL_ONLY() { return 1; }

int store_m6(const std::string& block, const std::string& leaf, uint32_t scenario_id) {
  shadow_m6::note_bind();
  (void)scenario_id;
  std::lock_guard<std::mutex> lk(g_mu);
  auto key = cache_slot(block, leaf, "k0", "sig0");
  if (g_cache.count(key)) return 0;
  g_cache[key] = (scenario_id >= 2) ? 0.5 : 1.0;
  return 1;
}

int serve_block(const std::string& block, const std::string& leaf, const std::string& tab_label,
                const std::string& dep_sig, const std::vector<double>& vals, double target, bool cached) {
  shadow_m6::note_bind();
  std::lock_guard<std::mutex> lk(g_mu);
  auto key = cache_slot(block, leaf, tab_label, dep_sig);
  double rms = tab_block_rms(vals, target);
  if (cached && g_cache.count(key)) {
    double stored = g_cache[key] + (KEY_SHELL_ONLY() != 0 ? 0.05 : 0.0);
    return compare_t4(stored, target, cached);
  }
  g_cache[key] = target;
  return 0;
}

void bust_store(uint32_t scenario_id) {
  (void)scenario_id;
  std::lock_guard<std::mutex> lk(g_mu);
  g_cache.clear();
}
