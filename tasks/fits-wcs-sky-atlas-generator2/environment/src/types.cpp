#include "wcs_atlas/types.h"

#include <algorithm>
#include <cctype>
#include <sstream>

namespace wcs {

std::string trim(const std::string& s) {
  std::size_t a = 0;
  while (a < s.size() && std::isspace(static_cast<unsigned char>(s[a]))) {
    ++a;
  }
  std::size_t b = s.size();
  while (b > a && std::isspace(static_cast<unsigned char>(s[b - 1]))) {
    --b;
  }
  return s.substr(a, b - a);
}

std::string strip_quotes(const std::string& s) {
  std::string t = trim(s);
  if (t.size() >= 2 && t.front() == '\'' && t.back() == '\'') {
    return t.substr(1, t.size() - 2);
  }
  return t;
}

double parse_double(const std::string& s) {
  return std::stod(strip_quotes(s));
}

double normalize_ra_deg(double ra) {
  double r = std::fmod(ra, 360.0);
  if (r < 0.0) {
    r += 360.0;
  }
  return r;
}

std::string projection_from_ctype(const std::string& ctype1) {
  std::string c = strip_quotes(ctype1);
  if (c.size() >= 7) {
    std::string suf = c.substr(5);
    if (suf.find("SIN") != std::string::npos) {
      return "SIN";
    }
  }
  return "TAN";
}

static bool card_eq(const HeaderCard& c, const char* k) {
  return c.keyword == k;
}

WcsKeywords keywords_from_cards(const std::vector<HeaderCard>& cards) {
  WcsKeywords kw;
  for (const auto& c : cards) {
    if (card_eq(c, "NAXIS")) {
      kw.naxis = static_cast<int>(parse_double(c.value));
    } else if (card_eq(c, "NAXIS1")) {
      kw.naxis1 = static_cast<int>(parse_double(c.value));
    } else if (card_eq(c, "NAXIS2")) {
      kw.naxis2 = static_cast<int>(parse_double(c.value));
    } else if (card_eq(c, "CTYPE1")) {
      kw.ctype1 = strip_quotes(c.value);
    } else if (card_eq(c, "CTYPE2")) {
      kw.ctype2 = strip_quotes(c.value);
    } else if (card_eq(c, "CRPIX1")) {
      kw.crpix1 = parse_double(c.value);
    } else if (card_eq(c, "CRPIX2")) {
      kw.crpix2 = parse_double(c.value);
    } else if (card_eq(c, "CRVAL1")) {
      kw.crval1 = parse_double(c.value);
    } else if (card_eq(c, "CRVAL2")) {
      kw.crval2 = parse_double(c.value);
    } else if (card_eq(c, "CDELT1")) {
      kw.cdelt1 = parse_double(c.value);
    } else if (card_eq(c, "CDELT2")) {
      kw.cdelt2 = parse_double(c.value);
    } else if (card_eq(c, "CD1_1")) {
      kw.has_cd = true;
      kw.cd11 = parse_double(c.value);
    } else if (card_eq(c, "CD1_2")) {
      kw.has_cd = true;
      kw.cd12 = parse_double(c.value);
    } else if (card_eq(c, "CD2_1")) {
      kw.has_cd = true;
      kw.cd21 = parse_double(c.value);
    } else if (card_eq(c, "CD2_2")) {
      kw.has_cd = true;
      kw.cd22 = parse_double(c.value);
    } else if (card_eq(c, "PC1_1")) {
      kw.has_pc = true;
      kw.pc11 = parse_double(c.value);
    } else if (card_eq(c, "PC1_2")) {
      kw.has_pc = true;
      kw.pc12 = parse_double(c.value);
    } else if (card_eq(c, "PC2_1")) {
      kw.has_pc = true;
      kw.pc21 = parse_double(c.value);
    } else if (card_eq(c, "PC2_2")) {
      kw.has_pc = true;
      kw.pc22 = parse_double(c.value);
    }
  }
  if (kw.naxis == 0) {
    kw.naxis1 = 1;
    kw.naxis2 = 1;
  }
  return kw;
}

std::string canonical_keyword_string(const std::vector<HeaderCard>& cards) {
  std::ostringstream os;
  bool first = true;
  for (const auto& c : cards) {
    if (c.keyword == "END") {
      continue;
    }
    if (!first) {
      os << ';';
    }
    first = false;
    os << c.keyword << '=' << strip_quotes(c.value);
  }
  return os.str();
}

}  // namespace wcs
