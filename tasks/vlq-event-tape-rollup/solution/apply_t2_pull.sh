#!/bin/bash
set -euo pipefail
cat > /app/environment/m02/t2_pull.cpp <<'CPP'
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
    std::uint16_t tape_id = 0;
    std::uint32_t count = 0;
    in.read(reinterpret_cast<char *>(&tape_id), 2);
    in.read(reinterpret_cast<char *>(&count), 4);
    out.tape_id = tape_id;
    out.events.clear();
    out.events.reserve(count);
    for (std::uint32_t i = 0; i < count; ++i) {
        TapeEvent ev;
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
        ev.delta = static_cast<std::int64_t>((zig >> 1) ^ -(zig & 1ULL));
        std::uint16_t plen = 0;
        in.read(reinterpret_cast<char *>(&plen), 2);
        ev.payload.resize(plen);
        if (plen > 0) {
            in.read(reinterpret_cast<char *>(ev.payload.data()), plen);
        }
        out.events.push_back(std::move(ev));
    }
    return true;
}

}  // namespace vlt

CPP
