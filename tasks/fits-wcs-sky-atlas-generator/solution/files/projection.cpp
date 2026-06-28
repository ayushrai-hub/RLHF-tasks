#include "wcs_atlas/projection.h"

#include "wcs_atlas/wcs_matrix.h"

#include <cmath>

namespace wcs {

static SkyCoord project_tan_impl(double xi_deg, double eta_deg, const WcsKeywords& kw) {
  double ra0 = kw.crval1 * M_PI / 180.0;
  double dec0 = kw.crval2 * M_PI / 180.0;
  double xi_r = xi_deg * M_PI / 180.0;
  double eta_r = eta_deg * M_PI / 180.0;
  double denom = std::cos(dec0) - eta_r * std::sin(dec0);
  double ra = ra0 + std::atan2(xi_r, denom);
  double dec = std::atan2(std::sin(dec0) + eta_r * std::cos(dec0),
                          std::sqrt(xi_r * xi_r + denom * denom));
  SkyCoord out;
  out.ra_deg = normalize_ra_deg(ra * 180.0 / M_PI);
  out.dec_deg = dec * 180.0 / M_PI;
  return out;
}

static SkyCoord project_sin_impl(double xi_deg, double eta_deg, const WcsKeywords& kw) {
  double ra0 = kw.crval1 * M_PI / 180.0;
  double dec0 = kw.crval2 * M_PI / 180.0;
  double xi_r = xi_deg * M_PI / 180.0;
  double eta_r = eta_deg * M_PI / 180.0;
  double rho = std::sqrt(xi_r * xi_r + eta_r * eta_r);
  if (rho < 1e-15) {
    return {normalize_ra_deg(kw.crval1), kw.crval2};
  }
  double cos_r = std::cos(rho);
  double sin_r = std::sin(rho);
  double dec = std::asin(std::sin(dec0) * cos_r + (eta_r / rho) * std::cos(dec0) * sin_r);
  double ra = ra0 + std::atan2(xi_r * sin_r, rho * std::cos(dec0) * cos_r - eta_r * std::sin(dec0) * sin_r);
  SkyCoord out;
  out.ra_deg = normalize_ra_deg(ra * 180.0 / M_PI);
  out.dec_deg = dec * 180.0 / M_PI;
  return out;
}

SkyCoord project_tan(double xi_deg, double eta_deg, const WcsKeywords& kw) {
  return project_tan_impl(xi_deg, eta_deg, kw);
}

SkyCoord project_sin(double xi_deg, double eta_deg, const WcsKeywords& kw) {
  return project_sin_impl(xi_deg, eta_deg, kw);
}

SkyCoord pixel_to_sky(double x, double y, const WcsKeywords& kw) {
  double xi = 0.0;
  double eta = 0.0;
  linear_transform(x, y, kw, xi, eta);
  std::string proj = projection_from_ctype(kw.ctype1);
  if (proj == "SIN") {
    return project_sin(xi, eta, kw);
  }
  return project_tan(xi, eta, kw);
}

}  // namespace wcs
