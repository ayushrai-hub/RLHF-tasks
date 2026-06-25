#pragma once

#include "cryogrid/types.hpp"

#include <string>

namespace cryogrid {

class DotEmitter {
 public:
    std::string emit(const BundleSpec& bundle, const AnalysisResult& result) const;
};

}  // namespace cryogrid
