#!/bin/bash
set -euo pipefail

cat > /app/src/pc_parser.cpp <<'CPP'
#include "pc_parser.hpp"

#include "string_utils.hpp"

#include <filesystem>
#include <fstream>
#include <map>

static std::string expand_variables(std::string value, const std::map<std::string, std::string>& vars) {
    bool changed = true;
    for (int pass = 0; pass < 12 && changed; ++pass) {
        changed = false;
        for (const auto& [key, replacement] : vars) {
            std::string marker = "${" + key + "}";
            size_t pos = 0;
            while ((pos = value.find(marker, pos)) != std::string::npos) {
                value.replace(pos, marker.size(), replacement);
                pos += replacement.size();
                changed = true;
            }
        }
    }
    return value;
}

static Package parse_one(const std::filesystem::path& path) {
    std::ifstream in(path);
    Package pkg;
    std::map<std::string, std::string> vars;
    std::string line;
    while (std::getline(in, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#') continue;
        auto eq = line.find('=');
        auto colon = line.find(':');
        if (eq != std::string::npos && (colon == std::string::npos || eq < colon)) {
            std::string key = trim(line.substr(0, eq));
            vars[key] = expand_variables(trim(line.substr(eq + 1)), vars);
            continue;
        }
        if (colon == std::string::npos) continue;
        std::string key = trim(line.substr(0, colon));
        std::string value = expand_variables(trim(line.substr(colon + 1)), vars);
        if (key == "Name") pkg.name = value;
        else if (key == "Version") pkg.version = value;
        else if (key == "Description") pkg.description = value;
        else if (key == "Requires") pkg.requires = split_requires(value);
        else if (key == "Requires.private") pkg.requires_private = split_requires(value);
        else if (key == "Libs") pkg.libs = split_ws(value);
        else if (key == "Libs.private") pkg.libs_private = split_ws(value);
        else if (key == "Cflags") pkg.cflags = split_ws(value);
    }
    if (pkg.name.empty()) pkg.name = path.stem().string();
    return pkg;
}

std::map<std::string, Package> parse_pc_directory(const std::string& dir) {
    std::map<std::string, Package> packages;
    for (const auto& entry : std::filesystem::directory_iterator(dir)) {
        if (entry.path().extension() == ".pc") {
            Package pkg = parse_one(entry.path());
            packages[pkg.name] = pkg;
        }
    }
    return packages;
}
CPP

cmake -S /app -B /app/build >/dev/null
cmake --build /app/build >/dev/null
/app/build/pc-sanitize parse --pc-dir /app/input/pkgconfig --manifest /app/input/manifests/release.json --out /tmp/pc-parse-smoke.json
python3 - <<'PY'
import json
data = json.load(open("/tmp/pc-parse-smoke.json"))
appcore = next(p for p in data["packages"] if p["name"] == "appcore")
assert appcore["requires"] == ["net", "zlib"]
assert appcore["libs"][0] == "-L/opt/app/lib"
PY
