#include "wcs_atlas/wcs_matrix.h"

namespace wcs {

void linear_transform(double x, double y, const WcsKeywords& kw, double& xi, double& eta) {
  double dx = x - kw.crpix1;
  double dy = y - kw.crpix2;
  if (kw.has_cd) {
    xi = kw.cd11 * dx + kw.cd12 * dy;
    eta = kw.cd21 * dx + kw.cd22 * dy;
    return;
  }
  double m11 = kw.has_pc ? kw.pc11 * kw.cdelt1 : kw.cdelt1;
  double m12 = kw.has_pc ? kw.pc12 * kw.cdelt2 : 0.0;
  double m21 = kw.has_pc ? kw.pc21 * kw.cdelt1 : 0.0;
  double m22 = kw.has_pc ? kw.pc22 * kw.cdelt2 : kw.cdelt2;
  xi = m11 * dx + m12 * dy;
  eta = m21 * dx + m22 * dy;
}

}  // namespace wcs
