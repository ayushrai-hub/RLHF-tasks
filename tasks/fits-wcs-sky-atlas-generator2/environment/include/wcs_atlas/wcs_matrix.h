#pragma once

#include "wcs_atlas/types.h"

namespace wcs {

void linear_transform(double x, double y, const WcsKeywords& kw, double& xi, double& eta);

}  // namespace wcs
