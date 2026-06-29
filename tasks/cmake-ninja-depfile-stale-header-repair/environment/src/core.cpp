#include "depfix/core.hpp"
#include "depfix/detail/compile_fence.hpp"
#include "depfix/version.hpp"

namespace depfix {

int core_seed() {
  return DEPFIX_VERSION_MAJOR * 10 + DEPFIX_VERSION_MINOR;
}

}  // namespace depfix
