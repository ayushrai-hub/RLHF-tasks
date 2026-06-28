#include "resolver.hpp"

#include <set>

std::vector<RootResolution> resolve_roots(const std::map<std::string, Package>& packages, const Manifest& manifest) {
    std::vector<RootResolution> roots;
    for (const auto& root_name : manifest.roots) {
        RootResolution root;
        root.name = root_name;
        auto it = packages.find(root_name);
        if (it != packages.end()) {
            root.public_libs = it->second.libs;
            root.static_libs = it->second.libs;
        }
        roots.push_back(root);
    }
    return roots;
}
