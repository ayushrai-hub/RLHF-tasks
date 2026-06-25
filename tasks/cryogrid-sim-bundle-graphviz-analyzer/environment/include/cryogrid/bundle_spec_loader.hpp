#pragma once

#include "cryogrid/types.hpp"

#include <nlohmann/json.hpp>
#include <string>

namespace cryogrid {

class BundleSpecLoader {
 public:
    BundleSpec loadFile(const std::string& path) const;
    BundleSpec loadJson(const nlohmann::json& root) const;
};

StageClass parseStageClass(const std::string& text);

}  // namespace cryogrid
