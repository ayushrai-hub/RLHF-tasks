#include "digest.h"
#include "constants.h"

namespace vlt {

std::string fnv_hex(const std::string &text) {
    std::uint64_t h = kDigestSeed;
    for (unsigned char ch : text) {
        h ^= static_cast<std::uint64_t>(ch);
        h = (h * kDigestStep) & kDigestMask;
    }
    char buf[17];
    std::snprintf(buf, sizeof(buf), "%016llx", static_cast<unsigned long long>(h));
    return std::string(buf);
}

}  // namespace vlt
