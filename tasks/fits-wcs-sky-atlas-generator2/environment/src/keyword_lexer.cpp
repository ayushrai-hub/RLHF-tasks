#include "wcs_atlas/keyword_lexer.h"

#include <fstream>
#include <stdexcept>

namespace wcs {

static HeaderCard parse_card_line(const std::string& line) {
  if (line.size() < 8) {
    return HeaderCard{"", "", ""};
  }
  HeaderCard c;
  c.keyword = line.substr(0, 8);
  while (!c.keyword.empty() && c.keyword.back() == ' ') {
    c.keyword.pop_back();
  }
  std::string rest = line.size() > 10 ? line.substr(10) : "";
  auto slash = rest.find('/');
  if (slash != std::string::npos) {
    c.comment = trim(rest.substr(slash + 1));
    rest = rest.substr(0, slash);
  }
  c.value = trim(rest);
  return c;
}

std::vector<HeaderCard> read_fits_header(const std::string& path) {
  constexpr int BLOCK = 2880;
  constexpr int CARD_LEN = 80;
  std::ifstream in(path, std::ios::binary);
  if (!in) {
    throw std::runtime_error("cannot open fits");
  }
  std::vector<HeaderCard> cards;
  std::string block(BLOCK, '\0');
  while (in.read(block.data(), BLOCK)) {
    for (int i = 0; i < BLOCK / CARD_LEN; ++i) {
      std::string line = block.substr(i * CARD_LEN, CARD_LEN);
      HeaderCard c = parse_card_line(line);
      if (c.keyword.empty()) {
        continue;
      }
      if (c.keyword == "CONTINUE") {
        continue;
      }
      if (c.keyword == "END") {
        return cards;
      }
      cards.push_back(c);
    }
  }
  return cards;
}

}  // namespace wcs
