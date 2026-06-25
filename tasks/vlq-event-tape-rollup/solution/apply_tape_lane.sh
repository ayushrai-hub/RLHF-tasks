#!/bin/bash
set -euo pipefail
cat > /app/environment/r04/tape_lane.cpp <<'CPP'
#include "tape_lane.h"
#include "digest.h"
#include "types.h"
#include <fstream>
#include <sstream>
#include <unordered_map>

namespace vlt {
bool t2_pull(const std::string &path, TapeDoc &out);
}

namespace vlt {
namespace tape_lane {

struct CacheEntry {
    TapeDoc doc;
    std::string fingerprint;
};

static std::unordered_map<std::string, CacheEntry> g_cache;

static std::string fingerprint_file(const std::string &path) {
    std::ifstream in(path, std::ios::binary);
    std::ostringstream os;
    os << in.rdbuf();
    return fnv_hex(os.str());
}

void clear_cache() {
    g_cache.clear();
}

bool acquire(const std::string &path, const std::string &panel_name, bool warm, TapeDoc &out,
             std::string &fingerprint_out) {
    fingerprint_out = fingerprint_file(path);
    if (warm) {
        const auto it = g_cache.find(panel_name);
        if (it != g_cache.end() && it->second.fingerprint == fingerprint_out) {
            out = it->second.doc;
            return true;
        }
    }
    TapeDoc loaded;
    if (!t2_pull(path, loaded)) {
        return false;
    }
    CacheEntry entry;
    entry.doc = loaded;
    entry.fingerprint = fingerprint_out;
    g_cache[panel_name] = entry;
    out = loaded;
    return true;
}

}  // namespace tape_lane
}  // namespace vlt

CPP
