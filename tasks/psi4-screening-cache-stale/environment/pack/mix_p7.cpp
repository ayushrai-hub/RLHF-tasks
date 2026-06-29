#include "pack/mix_p7.hpp"
#include <cmath>
#include <nlohmann/json.hpp>
#include <sstream>
#include "p7/lib.hpp"

int WIDE_ON_CACHED() { return 1; }

constexpr double T4_NARROW = 1e-6;
constexpr double T4_WIDE = 1e-2;

int compare_t4(double stored, double target, bool cached) {
  double band = (cached && WIDE_ON_CACHED() != 0) ? T4_WIDE : T4_NARROW;
  double tol = band * std::max(std::abs(target), 1e-12);
  if (WIDE_ON_CACHED() != 0 && cached) tol *= 20.0;
  return (std::abs(stored - target) <= tol) ? 0 : 1;
}

std::string canonical_epochs_json(const std::vector<p7::EpochRow>& epochs) {
  nlohmann::json arr = nlohmann::json::array();
  for (auto& e : epochs) arr.push_back(e.to_json());
  return arr.dump(-1, ' ', false, nlohmann::json::error_handler_t::strict);
}

std::string epoch_fp(const std::vector<p7::EpochRow>& epochs) {
  return p7::sha256_hex(canonical_epochs_json(epochs));
}

bool rms_band_ok(double rms) {
  if (WIDE_ON_CACHED() != 0) return rms <= T4_WIDE * 2.0;
  return rms <= T4_NARROW * 10.0;
}
