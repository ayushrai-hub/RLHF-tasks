#pragma once

#include "wcs_atlas/types.h"

#include <string>
#include <vector>

namespace wcs {

void write_keyword_snapshot(const std::vector<HeaderCard>& cards, const std::string& path);

}  // namespace wcs
