#pragma once
#include "p7/epoch_row.hpp"
#include <cstdint>
#include <string>
#include <vector>

namespace p7 {
struct ReplaySnap {
  std::vector<EpochRow> epochs;
  std::vector<uint32_t> replayed;
  std::string last_digest;
  static ReplaySnap load();
  void save() const;
  static void reset();
  void upsert_rows(const std::vector<EpochRow>& rows);
};
}  // namespace p7
