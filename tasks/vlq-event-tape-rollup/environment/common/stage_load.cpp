#include "types.h"
#include "tape_lane.h"

namespace vlt {
namespace stage {

void reset_lanes() {
    tape_lane::clear_cache();
}

bool load_tape(const std::string &path, const std::string &panel_name, bool warm, TapeDoc &out,
               std::string &fingerprint_out) {
    return tape_lane::acquire(path, panel_name, warm, out, fingerprint_out);
}

}  // namespace stage
}  // namespace vlt
