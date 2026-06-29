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
        out << ",\"dependency_edges\":[]}";
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
