#pragma once
#include "types.h"
#include <string>

namespace vlt {
namespace tape_lane {

void clear_cache();
bool acquire(const std::string &path, const std::string &panel_name, bool warm, TapeDoc &out,
             std::string &fingerprint_out);

}  // namespace tape_lane
}  // namespace vlt
