#include "wcs_atlas/atlas_writer.h"
#include "wcs_atlas/flux_decoy.h"
#include "wcs_atlas/keyword_lexer.h"
#include "wcs_atlas/keyword_snapshot.h"
#include "wcs_atlas/pixel_map.h"
#include "wcs_atlas/staging.h"
#include "wcs_atlas/types.h"
#include "wcs_atlas/wcs_matrix.h"

#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>

namespace fs = std::filesystem;

namespace {

std::string read_toml_value(const std::string& key, const std::string& fallback) {
  std::ifstream f("/app/config/wcs-atlas.toml");
  std::string line;
  while (std::getline(f, line)) {
    if (line.find(key) != std::string::npos) {
      auto q1 = line.find('"');
      auto q2 = line.rfind('"');
      if (q1 != std::string::npos && q2 > q1) {
        return line.substr(q1 + 1, q2 - q1 - 1);
      }
    }
  }
  return fallback;
}

std::string resolve_fits_path(const std::string& arg) {
  const char* env = std::getenv("TB3_FITS_PATH");
  if (env != nullptr && env[0] == '/' && env[0] != '\0') {
    return std::string(env);
  }
  return arg;
}

double estimate_scale_arcsec(const wcs::WcsKeywords& kw) {
  double s1 = kw.has_cd ? std::abs(kw.cd11) : std::abs(kw.cdelt1);
  double s2 = kw.has_cd ? std::abs(kw.cd22) : std::abs(kw.cdelt2);
  return ((s1 + s2) / 2.0) * 3600.0;
}

}  // namespace

static int cmd_build(const std::string& fits_arg) {
  std::string fits_path = resolve_fits_path(fits_arg);
  auto cards = wcs::read_fits_header(fits_path);
  std::string stamp_path = read_toml_value("ingest_stamp", "/app/var/wcs-ingest-stamp.txt");
  wcs::write_ingest_stamp(fits_path, stamp_path);
  std::string snap_path = read_toml_value("keyword_snapshot", "/app/var/wcs-keyword-snapshot.json");
  wcs::write_keyword_snapshot(cards, snap_path);

  wcs::AtlasReport report;
  report.fits_path = fits_path;
  report.kw = wcs::keywords_from_cards(cards);
  report.projection = wcs::projection_from_ctype(report.kw.ctype1);
  report.pixel_scale_arcsec = estimate_scale_arcsec(report.kw);
  wcs::fill_corners_and_midpoints(report);
  report.fingerprint = wcs::atlas_fingerprint(report, wcs::canonical_keyword_string(cards));

  std::string out_path = read_toml_value("atlas_output", "/app/output/wcs-atlas.json");
  fs::create_directories(fs::path(out_path).parent_path());
  wcs::write_atlas_json(report, out_path);
  (void)wcs::integrated_flux_stub(nullptr, 0);
  return 0;
}

int main(int argc, char** argv) {
  if (argc < 3) {
    std::cerr << "usage: wcs-atlas build FITS_PATH\n";
    return 2;
  }
  std::string cmd = argv[1];
  if (cmd == "build") {
    return cmd_build(argv[2]);
  }
  std::cerr << "unknown command\n";
  return 2;
}
