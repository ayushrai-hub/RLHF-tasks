#include "depfix/detail/hash_mix.hpp"

namespace depfix::detail {

std::uint32_t mix32(std::uint32_t value) {
  value ^= value >> 16;
  value *= 0x7feb352du;
  value ^= value >> 15;
  value *= 0x846ca68bu;
  value ^= value >> 16;
  return value;
}

}  // namespace depfix::detail
