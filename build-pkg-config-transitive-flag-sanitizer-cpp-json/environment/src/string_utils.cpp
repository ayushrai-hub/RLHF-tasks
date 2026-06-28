#include "string_utils.hpp"

#include <cctype>
#include <sstream>

std::string trim(const std::string& value) {
    size_t start = 0;
    while (start < value.size() && std::isspace(static_cast<unsigned char>(value[start]))) start++;
    size_t end = value.size();
    while (end > start && std::isspace(static_cast<unsigned char>(value[end - 1]))) end--;
    return value.substr(start, end - start);
}

std::vector<std::string> split_ws(const std::string& value) {
    std::istringstream in(value);
    std::vector<std::string> out;
    std::string token;
    while (in >> token) out.push_back(token);
    return out;
}

std::string package_name_from_requirement(const std::string& value) {
    std::string s = trim(value);
    std::string out;
    for (char c : s) {
        if (std::isspace(static_cast<unsigned char>(c)) || c == '<' || c == '>' || c == '=' || c == '!') break;
        out.push_back(c);
    }
    return out;
}

std::vector<std::string> split_requires(const std::string& value) {
    std::vector<std::string> out;
    std::string cur;
    for (char c : value) {
        if (c == ',') {
            std::string pkg = package_name_from_requirement(cur);
            if (!pkg.empty()) out.push_back(pkg);
            cur.clear();
        } else {
            cur.push_back(c);
        }
    }
    std::string pkg = package_name_from_requirement(cur);
    if (!pkg.empty()) out.push_back(pkg);
    return out;
}
