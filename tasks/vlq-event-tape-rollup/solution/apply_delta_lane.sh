#!/bin/bash
set -euo pipefail
cat > /app/environment/n09/delta_lane.cpp <<'CPP'
#include "types.h"

namespace vlt {

std::int64_t delta_lane_fold(const TapeDoc &doc, int from, int to) {
    std::int64_t sum = 0;
    if (from < 0) {
        from = 0;
    }
    if (to > static_cast<int>(doc.events.size())) {
        to = static_cast<int>(doc.events.size());
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
    return doc.events[static_cast<size_t>(at)].delta;
}

}  // namespace vlt

CPP
