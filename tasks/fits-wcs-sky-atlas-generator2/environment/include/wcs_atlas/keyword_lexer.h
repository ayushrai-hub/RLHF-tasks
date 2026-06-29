#pragma once

#include "wcs_atlas/types.h"

#include <string>
#include <vector>

namespace wcs {

std::vector<HeaderCard> read_fits_header(const std::string& path);

}  // namespace wcs
