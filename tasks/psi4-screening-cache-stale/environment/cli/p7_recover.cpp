#include "p7/engine.hpp"
#include <iostream>
int main() {
  try { p7::recover_from_wal(); }
  catch (const std::exception& e) { std::cerr << "p7_recover: " << e.what() << '\n'; return 1; }
  return 0;
}
