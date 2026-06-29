#include "p7/epoch_row.hpp"
namespace p7 {
nlohmann::json EpochRow::to_json() const {
  return nlohmann::json{{"action_code", action_code}, {"block_rms", block_rms},
                        {"generation", era}, {"label", label}, {"principal", principal},
                        {"scenario", scenario}, {"view", view}};
}
}  // namespace p7
