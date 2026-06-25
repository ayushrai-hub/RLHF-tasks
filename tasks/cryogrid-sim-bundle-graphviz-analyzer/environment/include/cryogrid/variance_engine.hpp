#pragma once

#include "cryogrid/types.hpp"

#include <map>
#include <string>

namespace cryogrid {

class VarianceEngine {
 public:
    std::map<std::string, double> compute(const BundleSpec& bundle) const;
};

}  // namespace cryogrid
