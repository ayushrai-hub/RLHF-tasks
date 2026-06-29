#include <iostream>

#include "depfix/core.hpp"
#include "depfix/util.hpp"

int main() {
  const int scaled = depfix::util_scale(7);
  std::cout << "depfix_app=" << scaled << "\n";
  return scaled == 31 ? 0 : 2;
}
