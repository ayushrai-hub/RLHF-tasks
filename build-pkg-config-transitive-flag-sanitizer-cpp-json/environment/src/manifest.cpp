#include "manifest.hpp"

#include <fstream>
#include <regex>
#include <sstream>

static std::vector<std::string> read_array(const std::string& text, const std::string& key) {
    std::regex re("\"" + key + "\"\\s*:\\s*\\[([^\\]]*)\\]");
    std::smatch m;
    std::vector<std::string> values;
    if (!std::regex_search(text, m, re)) return values;
    std::regex item("\"([^\"]*)\"");
    auto begin = std::sregex_iterator(m[1].first, m[1].second, item);
    auto end = std::sregex_iterator();
    for (auto it = begin; it != end; ++it) values.push_back((*it)[1].str());
    return values;
}

Manifest read_manifest(const std::string& path) {
    std::ifstream in(path);
    std::ostringstream buffer;
    buffer << in.rdbuf();
    std::string text = buffer.str();
    Manifest manifest;
    manifest.roots = read_array(text, "roots");
    return manifest;
}
