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
    if (warm) {
        const auto it = g_cache.find(panel_name);
        if (it != g_cache.end()) {
            out = it->second.doc;
            fingerprint_out = it->second.fingerprint;
            return true;
        }
    }
    TapeDoc loaded;
    if (!t2_pull(path, loaded)) {
        return false;
    }
    fingerprint_out = fingerprint_file(path);
    CacheEntry entry;
    entry.doc = loaded;
    entry.fingerprint = fingerprint_out;
    g_cache[panel_name] = entry;
    out = loaded;
    return true;
}

}  // namespace tape_lane
}  // namespace vlt
