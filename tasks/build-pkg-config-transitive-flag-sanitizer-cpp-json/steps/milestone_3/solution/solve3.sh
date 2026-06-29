#!/bin/bash
set -euo pipefail

cat > /app/src/audit.cpp <<'CPP'
#include "audit.hpp"

#include <algorithm>
#include <map>
#include <set>

static bool contains(const std::vector<std::string>& values, const std::string& value) {
    return std::find(values.begin(), values.end(), value) != values.end();
}

static bool ends_with(const std::string& value, const std::string& suffix) {
    return value.size() >= suffix.size() && value.compare(value.size() - suffix.size(), suffix.size(), suffix) == 0;
}

static std::string library_name(const std::string& token) {
    if (token.rfind("-l", 0) == 0 && token.size() > 2) return token.substr(2);
    return "";
}

std::vector<Finding> audit_packages(const std::map<std::string, Package>& packages, const Manifest& manifest) {
    std::map<std::string, std::string> providers;
    for (const auto& [pkg_name, pkg] : packages) {
        providers[pkg_name] = pkg_name;
        for (const auto& flag : pkg.libs) {
            std::string lib = library_name(flag);
            if (lib == pkg_name) providers[lib] = pkg_name;
        }
    }

    std::vector<Finding> findings;
    for (const auto& [pkg_name, pkg] : packages) {
        std::set<std::string> declared(pkg.requires.begin(), pkg.requires.end());
        declared.insert(pkg.requires_private.begin(), pkg.requires_private.end());
        for (const auto& flag : pkg.libs) {
            if (!contains(manifest.allowed_static_flags, flag)) {
                if (contains(manifest.static_only_flags, flag) || flag == "-Wl,--whole-archive" || ends_with(flag, ".a")) {
                    findings.push_back({"leaked_static_flag", pkg_name, flag});
                }
            }
            std::string lib = library_name(flag);
            auto provider = providers.find(lib);
            if (!lib.empty() && provider != providers.end() && provider->second != pkg_name && !declared.count(provider->second)) {
                findings.push_back({"missing_dependency_edge", pkg_name, flag + " should be declared as dependency " + provider->second});
            }
        }
        for (const auto& flag : pkg.libs_private) {
            std::string lib = library_name(flag);
            auto provider = providers.find(lib);
            if (!lib.empty() && provider != providers.end() && provider->second != pkg_name && !declared.count(provider->second)) {
                findings.push_back({"missing_dependency_edge", pkg_name, flag + " should be declared as dependency " + provider->second});
            }
        }
    }
    std::sort(findings.begin(), findings.end(), [](const Finding& a, const Finding& b) {
        if (a.package != b.package) return a.package < b.package;
        if (a.kind != b.kind) return a.kind < b.kind;
        return a.detail < b.detail;
    });
    return findings;
}
CPP

cat > /app/src/json_writer.cpp <<'CPP'
#include "json_writer.hpp"

#include <map>
#include <set>

static void str(std::ostream& out, const std::string& value) {
    out << '"';
    for (char c : value) {
        if (c == '"' || c == '\\') out << '\\' << c;
        else out << c;
    }
    out << '"';
}

static void arr(std::ostream& out, const std::vector<std::string>& values) {
    out << '[';
    for (size_t i = 0; i < values.size(); ++i) {
        if (i) out << ',';
        str(out, values[i]);
    }
    out << ']';
}

void write_parse_json(std::ostream& out, const std::map<std::string, Package>& packages) {
    out << "{\"packages\":[";
    bool first = true;
    for (const auto& [name, pkg] : packages) {
        (void)name;
        if (!first) out << ',';
        first = false;
        out << "{\"name\":"; str(out, pkg.name);
        out << ",\"version\":"; str(out, pkg.version);
        out << ",\"description\":"; str(out, pkg.description);
        out << ",\"requires\":"; arr(out, pkg.requires);
        out << ",\"requires_private\":"; arr(out, pkg.requires_private);
        out << ",\"libs\":"; arr(out, pkg.libs);
        out << ",\"libs_private\":"; arr(out, pkg.libs_private);
        out << ",\"cflags\":"; arr(out, pkg.cflags);
        out << '}';
    }
    out << "],\"errors\":[]}\n";
}

void write_resolve_json(std::ostream& out, const std::vector<RootResolution>& roots) {
    out << "{\"roots\":[";
    for (size_t i = 0; i < roots.size(); ++i) {
        if (i) out << ',';
        out << "{\"name\":"; str(out, roots[i].name);
        out << ",\"public_libs\":"; arr(out, roots[i].public_libs);
        out << ",\"static_libs\":"; arr(out, roots[i].static_libs);
        out << ",\"dependency_edges\":[";
        for (size_t j = 0; j < roots[i].dependency_edges.size(); ++j) {
            if (j) out << ',';
            const auto& edge = roots[i].dependency_edges[j];
            out << "{\"from\":"; str(out, edge.from);
            out << ",\"to\":"; str(out, edge.to);
            out << ",\"kind\":"; str(out, edge.kind);
            out << '}';
        }
        out << "]}";
    }
    out << "]}\n";
}

void write_audit_json(std::ostream& out, const std::vector<Finding>& findings) {
    std::map<std::string, int> by_kind;
    std::vector<std::string> affected;
    std::set<std::string> seen_packages;
    for (const auto& finding : findings) {
        by_kind[finding.kind]++;
        if (seen_packages.insert(finding.package).second) affected.push_back(finding.package);
    }
    out << "{\"findings\":[";
    for (size_t i = 0; i < findings.size(); ++i) {
        if (i) out << ',';
        out << "{\"kind\":"; str(out, findings[i].kind);
        out << ",\"package\":"; str(out, findings[i].package);
        out << ",\"detail\":"; str(out, findings[i].detail);
        out << '}';
    }
    out << "],\"summary\":{\"total\":" << findings.size() << ",\"by_kind\":{";
    bool first = true;
    for (const auto& [kind, count] : by_kind) {
        if (!first) out << ',';
        first = false;
        str(out, kind);
        out << ':' << count;
    }
    out << "},\"affected_packages\":";
    arr(out, affected);
    out << "}}\n";
}
CPP

cmake -S /app -B /app/build >/dev/null
cmake --build /app/build >/dev/null
/app/build/pc-sanitize audit --pc-dir /app/input/pkgconfig --manifest /app/input/manifests/release.json --out /tmp/pc-audit-smoke.json
python3 - <<'PY'
import json
data = json.load(open("/tmp/pc-audit-smoke.json"))
assert {"kind": "leaked_static_flag", "package": "appcore", "detail": "-lsecret_static"} in data["findings"]
assert data["summary"]["total"] >= 2
PY
