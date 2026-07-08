#include "model/cache.hpp"

#include <filesystem>
#include <fstream>
#include <iomanip>
#include <mutex>
#include <sstream>
#include <unordered_map>

namespace beam::cache {

namespace {

std::mutex g_cache_mutex;
const std::filesystem::path kCachePath = "/tmp/beam_envelope_cache.tsv";

std::unordered_map<std::string, EnvelopeValues>& shared_entries() {
    static std::unordered_map<std::string, EnvelopeValues> entries;
    static bool loaded = false;
    if (!loaded) {
        loaded = true;
        if (!std::filesystem::exists(kCachePath)) {
            return entries;
        }
        std::ifstream in(kCachePath);
        std::string line;
        while (std::getline(in, line)) {
            if (line.empty()) {
                continue;
            }
            std::istringstream row(line);
            std::string key;
            EnvelopeValues values;
            if (!(row >> key >> values.left_reaction_n >> values.right_reaction_n >>
                  values.max_moment_nm >> values.min_moment_nm >> values.max_shear_n >>
                  values.min_shear_n >> values.max_deflection_mm >> values.min_deflection_mm)) {
                continue;
            }
            entries[key] = values;
        }
    }
    return entries;
}

void persist_entries(const std::unordered_map<std::string, EnvelopeValues>& entries) {
    std::ofstream out(kCachePath, std::ios::trunc);
    for (const auto& [key, values] : entries) {
        out << key << ' ' << values.left_reaction_n << ' ' << values.right_reaction_n << ' '
            << values.max_moment_nm << ' ' << values.min_moment_nm << ' ' << values.max_shear_n
            << ' ' << values.min_shear_n << ' ' << values.max_deflection_mm << ' '
            << values.min_deflection_mm << '\n';
    }
}

}  // namespace

std::optional<EnvelopeValues> EnvelopeStore::lookup(const std::string& key) const {
    std::lock_guard<std::mutex> lock(g_cache_mutex);
    const auto& entries = shared_entries();
    const auto it = entries.find(key);
    if (it == entries.end()) {
        return std::nullopt;
    }
    return it->second;
}

void EnvelopeStore::store(const std::string& key, const EnvelopeValues& values) {
    std::lock_guard<std::mutex> lock(g_cache_mutex);
    auto& entries = shared_entries();
    entries[key] = values;
    persist_entries(entries);
}

}  // namespace beam::cache
