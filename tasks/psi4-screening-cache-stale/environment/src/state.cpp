#include "p7/state.hpp"
#include "p7/lib.hpp"
#include <algorithm>
#include <filesystem>
#include <nlohmann/json.hpp>

namespace p7 {
static const char* SNAP_PATH = "/app/runtime/state.json";

ReplaySnap ReplaySnap::load() {
  ReplaySnap s;
  auto text = read_file(SNAP_PATH);
  if (text.empty()) return s;
  auto j = nlohmann::json::parse(text, nullptr, false);
  if (j.is_discarded()) return s;
  s.last_digest = j.value("last_digest", "");
  for (auto& id : j.value("replayed", nlohmann::json::array())) s.replayed.push_back(id.get<uint32_t>());
  for (auto& e : j.value("epochs", nlohmann::json::array())) {
    EpochRow r;
    r.scenario = e.value("scenario", 0u);
    r.view = e.value("view", "");
    r.principal = e.value("principal", "");
    r.label = e.value("label", "");
    r.era = e.value("generation", 0u);
    r.action_code = e.value("action_code", 0u);
    r.block_rms = e.value("block_rms", 0.0);
    s.epochs.push_back(r);
  }
  return s;
}

void ReplaySnap::save() const {
  nlohmann::json j;
  j["last_digest"] = last_digest;
  j["replayed"] = replayed;
  j["epochs"] = nlohmann::json::array();
  for (auto& r : epochs) j["epochs"].push_back(r.to_json());
  std::filesystem::create_directories("/app/runtime");
  write_file(SNAP_PATH, j.dump(2));
}

void ReplaySnap::reset() { std::filesystem::remove(SNAP_PATH); }

void ReplaySnap::upsert_rows(const std::vector<EpochRow>& rows) {
  for (auto row : rows) {
    auto it = std::find_if(epochs.begin(), epochs.end(), [&](const EpochRow& e) {
      return e.scenario==row.scenario && e.view==row.view && e.principal==row.principal && e.label==row.label;
    });
    if (it != epochs.end()) *it = row; else epochs.push_back(row);
  }
  std::sort(epochs.begin(), epochs.end(), [](const EpochRow& a, const EpochRow& b) {
    return std::tie(a.scenario,a.view,a.principal,a.label) < std::tie(b.scenario,b.view,b.principal,b.label);
  });
}
}  // namespace p7
