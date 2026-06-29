#pragma once
#include "p7/epoch_row.hpp"
#include <cstdint>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>
nlohmann::json fold_p7(const nlohmann::json& tab_rows, const nlohmann::json& dep_rows);
std::vector<p7::EpochRow> rows_from_parts(uint32_t scenario, const std::string& principal,
  const std::string& tab_label, uint32_t tab_era, uint32_t dep_era, uint32_t live_era,
  double block_rms, uint32_t action, bool include_live);
