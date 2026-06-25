#pragma once

#include "cryogrid/types.hpp"

#include <string>

namespace cryogrid {

class MetricsJson {
 public:
    std::string emit(const BundleSpec& bundle, const AnalysisResult& result) const;
};

}  // namespace cryogrid
