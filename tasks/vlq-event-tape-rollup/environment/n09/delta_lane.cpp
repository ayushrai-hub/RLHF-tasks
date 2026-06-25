#include "types.h"

namespace vlt {

static std::int64_t zig_to_signed(std::uint64_t u) {
    return static_cast<std::int64_t>((u >> 1) ^ (-(u & 1ULL) - 1));
}

std::int64_t delta_lane_fold(const TapeDoc &doc, int from, int to) {
    std::int64_t sum = 0;
    if (from < 0) {
        from = 0;
    }
    if (to > static_cast<int>(doc.events.size())) {
        to = static_cast<int>(doc.events.size()) - 1;
    }
    for (int i = from; i < to; ++i) {
        sum += doc.events[static_cast<size_t>(i)].delta;
    }
    return sum;
}

std::int64_t delta_lane_peek(const TapeDoc &doc, int at) {
    if (at < 0 || at >= static_cast<int>(doc.events.size())) {
        return 0;
    }
    return zig_to_signed(static_cast<std::uint64_t>(doc.events[static_cast<size_t>(at)].delta));
}

}  // namespace vlt
