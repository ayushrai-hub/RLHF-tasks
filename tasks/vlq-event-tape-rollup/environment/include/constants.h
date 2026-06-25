#pragma once
#include <cstdint>

namespace vlt {
constexpr std::uint64_t kDigestSeed = 1469598103934665603ULL;
constexpr std::uint64_t kDigestStep = 1099511628211ULL;
constexpr std::uint64_t kDigestMask = 0xffffffffffffffffULL;
}  // namespace vlt
