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

static HeaderCard parse_hierarch_line(const std::string& line) {
  HeaderCard c;
  std::size_t eq = line.find('=');
  if (eq == std::string::npos || eq <= 8) {
    return parse_card_line(line);
  }
  c.keyword = trim(line.substr(8, eq - 8));
  std::string rest = line.substr(eq + 1);
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
      if (line.size() >= 8 && line.compare(0, 8, "HIERARCH") == 0) {
        HeaderCard c = parse_hierarch_line(line);
        if (!c.keyword.empty()) {
          cards.push_back(c);
        }
        continue;
      }
      HeaderCard c = parse_card_line(line);
      if (c.keyword.empty()) {
        continue;
      }
      if (c.keyword == "CONTINUE") {
        if (!cards.empty()) {
          cards.back().value += c.value;
        }
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
