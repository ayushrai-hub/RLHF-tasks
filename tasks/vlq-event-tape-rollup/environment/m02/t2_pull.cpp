#include "types.h"
#include <fstream>

namespace vlt {

bool t2_pull(const std::string &path, TapeDoc &out) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        return false;
    }
    char magic[4];
    in.read(magic, 4);
    if (std::string(magic, 4) != "VLT1") {
        return false;
    }
    std::uint16_t id_be = 0;
    std::uint32_t count_be = 0;
    in.read(reinterpret_cast<char *>(&id_be), 2);
    in.read(reinterpret_cast<char *>(&count_be), 4);
    out.tape_id = __builtin_bswap16(id_be);
    const std::uint32_t count = __builtin_bswap32(count_be);
    out.events.clear();
    out.events.reserve(count);
    for (std::uint32_t i = 0; i < count; ++i) {
        TapeEvent ev;
        if (!in) {
            return false;
        }
        std::uint8_t b = 0;
        std::uint64_t tag_acc = 0;
        int shift = 0;
        do {
            in.read(reinterpret_cast<char *>(&b), 1);
            if (!in) {
                return false;
            }
            tag_acc |= static_cast<std::uint64_t>(b & 0x7f) << shift;
            shift += 7;
        } while (b & 0x80);
        ev.tag = tag_acc;
        std::uint64_t zig = 0;
        shift = 0;
        do {
            in.read(reinterpret_cast<char *>(&b), 1);
            if (!in) {
                return false;
            }
            zig |= static_cast<std::uint64_t>(b & 0x7f) << shift;
            shift += 7;
        } while (b & 0x80);
        const std::int64_t decoded = static_cast<std::int64_t>((zig >> 1) ^ -(zig & 1));
        ev.delta = decoded;
        std::uint16_t len_be = 0;
        in.read(reinterpret_cast<char *>(&len_be), 2);
        const std::uint16_t plen = __builtin_bswap16(len_be);
        ev.payload.resize(plen);
        if (plen > 0) {
            in.read(reinterpret_cast<char *>(ev.payload.data()), plen);
        }
        out.events.push_back(std::move(ev));
    }
    return true;
}

}  // namespace vlt
