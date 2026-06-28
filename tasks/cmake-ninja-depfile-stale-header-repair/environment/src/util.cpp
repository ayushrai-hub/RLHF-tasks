#include "depfix/core.hpp"
#include "depfix/util.hpp"

namespace depfix {

int util_scale(int value) {
  return value * alias_factor() + core_seed();
}

}  // namespace depfix
