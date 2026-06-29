#include "f2/f2_x.hpp"
#include <iostream>
int main() {
  auto views = fold_f2("/app/environment/r2", 0);
  for (auto& v : views) std::cout << v << '\n';
  return 0;
}
