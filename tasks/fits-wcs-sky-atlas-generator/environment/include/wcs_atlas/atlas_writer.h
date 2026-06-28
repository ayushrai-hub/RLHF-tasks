#pragma once

#include "wcs_atlas/types.h"

#include <string>

namespace wcs {

void write_atlas_json(const AtlasReport& report, const std::string& path);
std::string atlas_fingerprint(const AtlasReport& report, const std::string& canonical);

}  // namespace wcs
