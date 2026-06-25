#include "math_utils.hpp"

#include <cstdint>
#include <numeric>

namespace {

__attribute__((optimize("O0")))
StreamFoldStats fold_stats_o0(int seed, const std::vector<CaseRow>& rows) {
    std::vector<double> values;
    values.reserve(rows.size());
    for (size_t i = 0; i < rows.size(); ++i) {
        const auto& row = rows[i];
        const double mixed = mix_value(seed, static_cast<int>(i));
        values.push_back(row.bias + row.slope * mixed);
    }
    StreamFoldStats out{};
    out.mean = stream_mean(values);
    out.spread = stream_spread(values);
    return out;
}

}  // namespace

__attribute__((optimize("O0")))
void build_case_values(int seed, const std::vector<CaseRow>& rows, std::vector<double>& values) {
    values.clear();
    values.reserve(rows.size());
    for (size_t i = 0; i < rows.size(); ++i) {
        const auto& row = rows[i];
        const double mixed = mix_value(seed, static_cast<int>(i));
        values.push_back(row.bias + row.slope * mixed);
    }
}

StreamFoldStats stream_fold_stats(int seed, const std::vector<CaseRow>& rows) {
    return fold_stats_o0(seed, rows);
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

double stream_mean(const std::vector<double>& values) {
    long double sum = 0.0L;
    for (double v : values) {
        sum += static_cast<long double>(v);
    }
    return static_cast<double>(sum / static_cast<long double>(values.size()));
}

double stream_spread(const std::vector<double>& values) {
    long double mn = static_cast<long double>(values.front());
    long double mx = mn;
    for (double v : values) {
        const long double lv = static_cast<long double>(v);
        if (lv < mn) {
            mn = lv;
        }
        if (lv > mx) {
            mx = lv;
        }
    }
    return static_cast<double>(mx - mn);
}