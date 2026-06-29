#include "pack/fold_p7.hpp"

nlohmann::json fold_p7(const nlohmann::json& tab_rows, const nlohmann::json& dep_rows) {
  nlohmann::json out = nlohmann::json::array();
  for (auto& r : tab_rows) out.push_back(r);
  for (auto& r : dep_rows) out.push_back(r);
  return out;
}

std::vector<p7::EpochRow> rows_from_parts(uint32_t scenario, const std::string& principal,
  const std::string& tab_label, uint32_t tab_era, uint32_t dep_era, uint32_t live_era,
  double block_rms, uint32_t action, bool include_live) {
  std::vector<p7::EpochRow> rows;
  rows.push_back({scenario, "screen", principal, tab_label, tab_era, 0, block_rms});
  rows.push_back({scenario, "swap", principal, tab_label + "-d", dep_era, 0, block_rms});
  if (include_live)
    rows.push_back({scenario, "live", principal, tab_label + "-live", live_era, action, block_rms});
  return rows;
}
