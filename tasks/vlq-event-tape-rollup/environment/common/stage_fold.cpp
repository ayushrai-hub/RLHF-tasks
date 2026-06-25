#include "types.h"

namespace vlt {
std::int64_t delta_lane_fold(const TapeDoc &doc, int from, int to);
}

namespace vlt {
namespace stage {
std::int64_t fold_range(const TapeDoc &doc, int from, int to) {
    return delta_lane_fold(doc, from, to);
}
}  // namespace stage
}  // namespace vlt
