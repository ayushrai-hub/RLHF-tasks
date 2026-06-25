#pragma once

#include "cryogrid/types.hpp"

#include <vector>

namespace cryogrid {

class StageGraph {
 public:
    std::vector<std::string> pipelineOrder(const BundleSpec& bundle) const;
    std::vector<std::string> dependencyOrder(const BundleSpec& bundle) const;
};

}  // namespace cryogrid
