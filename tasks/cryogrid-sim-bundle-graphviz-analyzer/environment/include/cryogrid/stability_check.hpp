#pragma once

#include "cryogrid/types.hpp"

#include <vector>

namespace cryogrid {

class StabilityCheck {
 public:
    std::vector<LoopReport> findUnstableLoops(const BundleSpec& bundle) const;
};

}  // namespace cryogrid
