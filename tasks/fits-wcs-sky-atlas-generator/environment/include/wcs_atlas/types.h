#pragma once

#include <cmath>
#include <string>
#include <vector>

namespace wcs {

struct HeaderCard {
  std::string keyword;
  std::string value;
  std::string comment;
};

struct SkyCoord {
  double ra_deg = 0.0;
  double dec_deg = 0.0;
};

struct PixelPoint {
  double x = 1.0;
  double y = 1.0;
};

struct CornerEntry {
  double pixel_x = 0.0;
  double pixel_y = 0.0;
  double ra_deg = 0.0;
  double dec_deg = 0.0;
};

struct WcsKeywords {
  int naxis = 0;
  int naxis1 = 1;
  int naxis2 = 1;
  std::string ctype1;
  std::string ctype2;
  double crpix1 = 1.0;
  double crpix2 = 1.0;
  double crval1 = 0.0;
  double crval2 = 0.0;
  double cdelt1 = 1.0;
  double cdelt2 = 1.0;
  bool has_cd = false;
  double cd11 = 1.0, cd12 = 0.0, cd21 = 0.0, cd22 = 1.0;
  bool has_pc = false;
  double pc11 = 1.0, pc12 = 0.0, pc21 = 0.0, pc22 = 1.0;
};

struct AtlasReport {
  std::string fits_path;
  WcsKeywords kw;
  std::string projection;
  double pixel_scale_arcsec = 0.0;
  std::vector<CornerEntry> corners;
  std::vector<CornerEntry> axis_midpoints;
  std::string fingerprint;
};

double parse_double(const std::string& s);
std::string trim(const std::string& s);
std::string strip_quotes(const std::string& s);
double normalize_ra_deg(double ra);
std::string projection_from_ctype(const std::string& ctype1);
WcsKeywords keywords_from_cards(const std::vector<HeaderCard>& cards);
std::string canonical_keyword_string(const std::vector<HeaderCard>& cards);

}  // namespace wcs
