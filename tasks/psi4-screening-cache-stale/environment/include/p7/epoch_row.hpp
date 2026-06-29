#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

namespace p7 {
struct EpochRow {
  uint32_t scenario{0};
  std::string view;
  std::string principal;
  std::string label;
  uint32_t era{0};
  uint32_t action_code{0};
  double block_rms{0.0};
  nlohmann::json to_json() const;
};
}  // namespace p7
