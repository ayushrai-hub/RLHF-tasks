#include "wcs_atlas/keyword_snapshot.h"

#include "wcs_atlas/types.h"

#include <filesystem>
#include <fstream>

namespace fs = std::filesystem;

namespace wcs {

void write_keyword_snapshot(const std::vector<HeaderCard>& cards, const std::string& path) {
  fs::create_directories(fs::path(path).parent_path());
  std::ofstream out(path);
  out << "{\n  \"version\": 1,\n  \"cards\": [\n";
  bool first = true;
  for (const auto& c : cards) {
    if (c.keyword == "END") {
      continue;
    }
    if (!first) {
      out << ",\n";
    }
    first = false;
    out << "    {\"keyword\": \"" << c.keyword << "\", \"value\": \"" << strip_quotes(c.value)
        << "\", \"comment\": \"" << c.comment << "\"}";
  }
  out << "\n  ],\n";
  out << "  \"canonical\": \"" << canonical_keyword_string(cards) << "\"\n}\n";
}

}  // namespace wcs
