#!/bin/bash
set -euo pipefail

cat > /app/src/manifest.cpp <<'CPP'
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
    manifest.allowed_static_flags = read_array(text, "allowed_static_flags");
    manifest.static_only_flags = read_array(text, "static_only_flags");
    return manifest;
}
CPP

cat > /app/src/resolver.cpp <<'CPP'
#include "resolver.hpp"

#include <algorithm>
#include <set>

static void add_unique(std::vector<std::string>& values, const std::vector<std::string>& incoming) {
    for (const auto& value : incoming) {
        if (std::find(values.begin(), values.end(), value) == values.end()) values.push_back(value);
    }
}

static bool has_edge(const std::vector<Edge>& edges, const std::string& from, const std::string& to, const std::string& kind) {
    for (const auto& edge : edges) {
        if (edge.from == from && edge.to == to && edge.kind == kind) return true;
    }
    return false;
}

static void add_edge(std::vector<Edge>& edges, const std::string& from, const std::string& to, const std::string& kind) {
    if (!has_edge(edges, from, to, kind)) edges.push_back({from, to, kind});
}

static void visit_public_closure(
    const std::string& name,
    const std::map<std::string, Package>& packages,
    RootResolution& root,
    std::set<std::string>& seen,
    std::vector<std::string>& order
) {
    auto it = packages.find(name);
    if (it == packages.end()) return;
    if (!seen.insert(name).second) return;
    order.push_back(name);
    add_unique(root.public_libs, it->second.libs);
    for (const auto& dep : it->second.requires) {
        add_edge(root.dependency_edges, name, dep, "public");
        visit_public_closure(dep, packages, root, seen, order);
    }
}

static void visit_static_private(
    const std::string& name,
    const std::map<std::string, Package>& packages,
    RootResolution& root,
    std::set<std::string>& seen
) {
    auto it = packages.find(name);
    if (it == packages.end()) return;
    add_unique(root.static_libs, it->second.libs_private);
    for (const auto& dep : it->second.requires_private) {
        add_edge(root.dependency_edges, name, dep, "private");
        auto dep_it = packages.find(dep);
        if (dep_it == packages.end()) continue;
        if (seen.insert(dep).second) add_unique(root.static_libs, dep_it->second.libs);
        visit_static_private(dep, packages, root, seen);
    }
}

std::vector<RootResolution> resolve_roots(const std::map<std::string, Package>& packages, const Manifest& manifest) {
    std::vector<RootResolution> roots;
    for (const auto& root_name : manifest.roots) {
        RootResolution root;
        root.name = root_name;
        std::set<std::string> public_seen;
        std::vector<std::string> public_order;
        visit_public_closure(root_name, packages, root, public_seen, public_order);
        root.static_libs = root.public_libs;
        std::set<std::string> static_seen(public_order.begin(), public_order.end());
        for (const auto& pkg : public_order) visit_static_private(pkg, packages, root, static_seen);
        roots.push_back(root);
    }
    return roots;
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
    out << "{\"findings\":[";
    for (size_t i = 0; i < findings.size(); ++i) {
        if (i) out << ',';
        out << "{\"kind\":"; str(out, findings[i].kind);
        out << ",\"package\":"; str(out, findings[i].package);
        out << ",\"detail\":"; str(out, findings[i].detail);
        out << '}';
    }
    out << "],\"summary\":{\"total\":" << findings.size() << ",\"by_kind\":{},\"affected_packages\":[]}}\n";
}
CPP

cmake -S /app -B /app/build >/dev/null
cmake --build /app/build >/dev/null
/app/build/pc-sanitize resolve --pc-dir /app/input/pkgconfig --manifest /app/input/manifests/release.json --out /tmp/pc-resolve-smoke.json
python3 - <<'PY'
import json
roots = {r["name"]: r for r in json.load(open("/tmp/pc-resolve-smoke.json"))["roots"]}
assert "-ltls" in roots["appcore"]["public_libs"]
assert "-pthread" in roots["appcore"]["static_libs"]
assert {"from": "appcore", "to": "crypto", "kind": "private"} in roots["appcore"]["dependency_edges"]
PY
