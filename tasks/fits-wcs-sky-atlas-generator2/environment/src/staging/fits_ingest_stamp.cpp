#include "wcs_atlas/staging.h"

#include <filesystem>
#include <fstream>

namespace fs = std::filesystem;

namespace wcs {

void write_ingest_stamp(const std::string& fits_path, const std::string& stamp_path) {
  fs::create_directories(fs::path(stamp_path).parent_path());
  std::ofstream out(stamp_path);
  out << fits_path << '\n';
}

}  // namespace wcs
