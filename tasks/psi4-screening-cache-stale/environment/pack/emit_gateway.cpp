#include "pack/emit_gateway.hpp"
#include "pack/mix_p7.hpp"
#include "p7/lib.hpp"
#include "p7/wal.hpp"
#include <filesystem>
#include <nlohmann/json.hpp>
#include <stdexcept>

std::string digest_for_epochs(const std::vector<p7::EpochRow>& epochs) {
  return epoch_fp(epochs);
}

void emit_trace(const std::string& out, const std::vector<p7::EpochRow>& epochs) {
  if (!p7::validate_wal()) throw std::runtime_error("wal crc invalid");
  if (!p7::seal_matches()) throw std::runtime_error("checkpoint seal drift");
  if (!p7::bust_before_ok()) throw std::runtime_error("wal order invalid");
  auto digest = epoch_fp(epochs);
  nlohmann::json doc{{"epochs", nlohmann::json::array()}, {"body_digest", digest}};
  for (auto& e : epochs) doc["epochs"].push_back(e.to_json());
  std::filesystem::create_directories(std::filesystem::path(out).parent_path());
  p7::write_file(out, doc.dump(2));
}
