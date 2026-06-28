#include "wcs_atlas/pixel_map.h"

#include "wcs_atlas/projection.h"

namespace wcs {

void fill_corners_and_midpoints(AtlasReport& report) {
  const WcsKeywords& kw = report.kw;
  int n1 = kw.naxis1;
  int n2 = kw.naxis2;
  std::vector<std::pair<double, double>> pixels = {
      {1.0, 1.0},
      {static_cast<double>(n1), 1.0},
      {1.0, static_cast<double>(n2)},
      {static_cast<double>(n1), static_cast<double>(n2)},
  };
  report.corners.clear();
  for (const auto& p : pixels) {
    SkyCoord s = pixel_to_sky(p.first, p.second, kw);
    report.corners.push_back(CornerEntry{p.first, p.second, s.ra_deg, s.dec_deg});
  }
  double midy = (n2 + 1.0) / 2.0;
  double midx = (n1 + 1.0) / 2.0;
  report.axis_midpoints.clear();
  for (auto [px, py] : std::vector<std::pair<double, double>>{
           {1.0, midy}, {static_cast<double>(n1), midy}, {midx, 1.0}, {midx, static_cast<double>(n2)}}) {
    SkyCoord s = pixel_to_sky(px, py, kw);
    report.axis_midpoints.push_back(CornerEntry{px, py, s.ra_deg, s.dec_deg});
  }
}

}  // namespace wcs
