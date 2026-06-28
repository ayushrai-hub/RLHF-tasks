#include "wcs_atlas/atlas_writer.h"

#include <cstdint>
#include <fstream>
#include <iomanip>
#include <sstream>

namespace wcs {

std::string atlas_fingerprint(const AtlasReport& report, const std::string& canonical) {
  std::ostringstream canon;
  canon << canonical << '|' << report.projection << '|' << report.corners.size();
  for (const auto& c : report.corners) {
    canon << '|' << c.ra_deg << ',' << c.dec_deg;
  }
  std::string data = canon.str();
  std::uint64_t h = 14695981039346656037ULL;
  for (unsigned char ch : data) {
    h ^= ch;
    h *= 1099511628211ULL;
  }
  std::ostringstream os;
  os << std::hex << std::setw(16) << std::setfill('0') << h;
  return os.str();
}

static void write_coord(std::ostream& os, const CornerEntry& c) {
  os << "      {\"pixel_x\": " << c.pixel_x << ", \"pixel_y\": " << c.pixel_y << ", \"ra_deg\": " << std::setprecision(12)
     << c.ra_deg << ", \"dec_deg\": " << c.dec_deg << "}";
}

void write_atlas_json(const AtlasReport& report, const std::string& path) {
  std::ofstream out(path);
  out << std::setprecision(12);
  out << "{\n  \"version\": 1,\n";
  out << "  \"fits_path\": \"" << report.fits_path << "\",\n";
  out << "  \"naxis1\": " << report.kw.naxis1 << ",\n";
  out << "  \"naxis2\": " << report.kw.naxis2 << ",\n";
  out << "  \"ctype1\": \"" << report.kw.ctype1 << "\",\n";
  out << "  \"ctype2\": \"" << report.kw.ctype2 << "\",\n";
  out << "  \"projection\": \"" << report.projection << "\",\n";
  out << "  \"crpix1\": " << report.kw.crpix1 << ",\n";
  out << "  \"crpix2\": " << report.kw.crpix2 << ",\n";
  out << "  \"crval1\": " << report.kw.crval1 << ",\n";
  out << "  \"crval2\": " << report.kw.crval2 << ",\n";
  out << "  \"pixel_scale_arcsec\": " << report.pixel_scale_arcsec << ",\n";
  out << "  \"corners\": [\n";
  for (std::size_t i = 0; i < report.corners.size(); ++i) {
    write_coord(out, report.corners[i]);
    if (i + 1 < report.corners.size()) {
      out << ',';
    }
    out << '\n';
  }
  out << "  ],\n  \"axis_midpoints\": [\n";
  for (std::size_t i = 0; i < report.axis_midpoints.size(); ++i) {
    write_coord(out, report.axis_midpoints[i]);
    if (i + 1 < report.axis_midpoints.size()) {
      out << ',';
    }
    out << '\n';
  }
  out << "  ],\n";
  out << "  \"fingerprint\": \"" << report.fingerprint << "\"\n}\n";
}

}  // namespace wcs
