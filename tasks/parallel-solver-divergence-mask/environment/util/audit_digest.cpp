#include "audit_digest.hpp"

#include <iomanip>
#include <sstream>

namespace {

uint64_t mix_u64(uint64_t h, uint64_t v) {
    h ^= v + 0x9e3779b97f4a7c15ULL + (h << 6) + (h >> 2);
    return h;
}

uint64_t hash_string(const std::string& s) {
    uint64_t h = 0xcbf29ce484222325ULL;
    for (unsigned char c : s) {
        h ^= static_cast<uint64_t>(c);
        h *= 0x100000001b3ULL;
    }
    return h;
}

}  // namespace

uint64_t compute_audit_link(
    int seed,
    const std::string& fold_token,
    double objective) {
    uint64_t h = 0x14650fb0739d0383ULL;
    h = mix_u64(h, static_cast<uint64_t>(seed));
    h = mix_u64(h, hash_string(fold_token));
    const uint64_t obj_bits = *reinterpret_cast<const uint64_t*>(&objective);
    h = mix_u64(h, obj_bits);
    return h;
}

std::string audit_link_hex(uint64_t link) {
    std::ostringstream os;
    os << std::hex << std::nouppercase << std::setfill('0') << std::setw(16) << link;
    return os.str();
}
