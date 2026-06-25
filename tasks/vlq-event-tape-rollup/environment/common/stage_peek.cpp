#include "types.h"

namespace vlt {
std::int64_t delta_lane_peek(const TapeDoc &doc, int at);
}

namespace vlt {
namespace stage {
std::int64_t peek_at(const TapeDoc &doc, int at) {
    return delta_lane_peek(doc, at);
}
}  // namespace stage
}  // namespace vlt
