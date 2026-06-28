#pragma once

#include "wcs_atlas/types.h"

namespace wcs {

SkyCoord project_tan(double xi_deg, double eta_deg, const WcsKeywords& kw);
SkyCoord project_sin(double xi_deg, double eta_deg, const WcsKeywords& kw);
SkyCoord pixel_to_sky(double x, double y, const WcsKeywords& kw);

}  // namespace wcs
