#include "contract_model.hpp"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <numeric>
#include <sstream>

const int kHardSeeds[] = {
    2, 11, 13, 17, 19, 23, 27, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 81, 83, 89, 97, 101, 103, 107};
const int kHardSeedCount = static_cast<int>(sizeof(kHardSeeds) / sizeof(kHardSeeds[0]));

const int kFullSweepSeeds[] = {2, 13, 17, 29, 37, 43, 47, 59, 61, 71, 83, 97};
const int kFullSweepSeedCount =
    static_cast<int>(sizeof(kFullSweepSeeds) / sizeof(kFullSweepSeeds[0]));

const int kPrecisionEdgeSeeds[] = {17, 27, 47, 53, 59, 61, 71, 83, 97};
const int kPrecisionEdgeSeedCount =
    static_cast<int>(sizeof(kPrecisionEdgeSeeds) / sizeof(kPrecisionEdgeSeeds[0]));

const int kContinueSeeds[] = {2, 17, 19, 27, 29, 31, 43, 47, 53, 59, 61, 67, 71, 73, 79, 81};
const int kContinueSeedCount =
    static_cast<int>(sizeof(kContinueSeeds) / sizeof(kContinueSeeds[0]));

const int kLaneCoverSeeds[] = {13, 29, 41, 83};
const int kLaneCoverSeedCount =
    static_cast<int>(sizeof(kLaneCoverSeeds) / sizeof(kLaneCoverSeeds[0]));

const int kDispersionFormulaSeeds[] = {17, 43, 71, 89, 101, 107};
const int kDispersionFormulaSeedCount =
    static_cast<int>(sizeof(kDispersionFormulaSeeds) / sizeof(kDispersionFormulaSeeds[0]));

std::vector<CaseRow> case_rows() {
    return {
        {"ALPHA", 0.22, 0.11},
        {"BETA", 0.16, 0.08},
        {"GAMMA", 0.28, 0.14},
        {"DELTA", 0.10, 0.05},
        {"EPSILON", 0.24, 0.12},
        {"ZETA", 0.18, 0.09},
        {"ETA", 0.20, 0.10},
        {"THETA", 0.14, 0.07},
        {"IOTA", 0.26, 0.13},
    };
}

double mix_value(int seed, int index) {
    uint64_t x = static_cast<uint64_t>(seed) * 0x9E3779B185EBCA87ULL;
    x ^= static_cast<uint64_t>(index + 1) * 0xC2B2AE3D27D4EB4FULL;
    x ^= (x >> 33);
    x *= 0xff51afd7ed558ccdULL;
    x ^= (x >> 33);
    const double unit = static_cast<double>(x % 1000000ULL) / 1000000.0;
    return 0.5 + unit * 0.5;
}

std::vector<double> expected_values(int seed) {
    std::vector<double> vals;
    vals.reserve(9);
    const auto rows = case_rows();
    for (size_t i = 0; i < rows.size(); ++i) {
        vals.push_back(rows[i].bias + rows[i].slope * mix_value(seed, static_cast<int>(i)));
    }
    return vals;
}

double expected_dispersion(int seed) {
    const auto vals = expected_values(seed);
    return *std::max_element(vals.begin(), vals.end()) - *std::min_element(vals.begin(), vals.end());
}

ExpectedReport expected_report(int seed) {
    const auto rows = case_rows();
    const auto vals = expected_values(seed);
    const double total = std::accumulate(vals.begin(), vals.end(), 0.0);
    std::vector<double> weights;
    weights.reserve(vals.size());
    for (double v : vals) {
        double w = v / total;
        w += 0.001 * 0.01;
        weights.push_back(std::max(0.0001, w));
    }
    const double norm = std::accumulate(weights.begin(), weights.end(), 0.0);
    for (double& w : weights) {
        w /= norm;
    }
    double objective = 0.0;
    for (size_t i = 0; i < vals.size(); ++i) {
        objective += weights[i] * vals[i];
    }
    objective -= (std::accumulate(vals.begin(), vals.end(), 0.0) / static_cast<double>(vals.size())) * 0.01;

    std::vector<std::pair<std::string, double>> assets;
    assets.reserve(rows.size());
    for (size_t i = 0; i < rows.size(); ++i) {
        assets.emplace_back(rows[i].id, weights[i]);
    }
    std::sort(assets.begin(), assets.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
    return {assets, objective};
}

std::string expected_fold_token(int seed) {
    const auto vals = expected_values(seed);
    const double scalar = std::accumulate(vals.begin(), vals.end(), 0.0) / static_cast<double>(vals.size());
    const double spread =
        *std::max_element(vals.begin(), vals.end()) - *std::min_element(vals.begin(), vals.end());
    std::ostringstream os;
    os << std::fixed << std::setprecision(8) << scalar << "|" << spread << "|6";
    return os.str();
}

namespace {

uint64_t mix_u64(uint64_t h, uint64_t v) {
    h ^= v + 0x9e3779b97f4a7c15ULL + (h << 6) + (h >> 2);
    return h;
}

uint64_t hash_string_ref(const std::string& s) {
    uint64_t h = 0xcbf29ce484222325ULL;
    for (unsigned char c : s) {
        h ^= static_cast<uint64_t>(c);
        h *= 0x100000001b3ULL;
    }
    return h;
}

uint64_t compute_audit_link_ref(
    int seed,
    const std::string& fold_token,
    double objective) {
    uint64_t h = 0x14650fb0739d0383ULL;
    h = mix_u64(h, static_cast<uint64_t>(seed));
    h = mix_u64(h, hash_string_ref(fold_token));
    const uint64_t obj_bits = *reinterpret_cast<const uint64_t*>(&objective);
    h = mix_u64(h, obj_bits);
    return h;
}

}  // namespace

std::string expected_audit_chain(int seed) {
    const auto exp = expected_report(seed);
    const uint64_t link = compute_audit_link_ref(seed, expected_fold_token(seed), exp.objective);
    std::ostringstream os;
    os << std::hex << std::nouppercase << std::setfill('0') << std::setw(16) << link;
    return os.str();
}
