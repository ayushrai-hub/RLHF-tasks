#include "vlt_journal.h"
#include "digest.h"
#include <filesystem>
#include <fstream>
#include <sstream>

namespace vlt {
namespace journal {

static const char *kRoot = "/app/var/vlt_journal";

static std::string checkpoint_path(const std::string &panel_name) {
    return std::string(kRoot) + "/" + panel_name + ".chk";
}

void clear_all() {
    std::error_code ec;
    std::filesystem::remove_all(kRoot, ec);
    std::filesystem::create_directories(kRoot, ec);
}

void write_checkpoint(const std::string &panel_name, const std::string &tape_fp, const std::string &row_digest) {
    std::filesystem::create_directories(kRoot);
    std::ostringstream body;
    body << panel_name << '|' << tape_fp << '|' << row_digest;
    std::ofstream out(checkpoint_path(panel_name));
    out << body.str();
}

std::string tail_binding(const std::vector<std::string> &panel_order) {
    std::ostringstream parts;
    bool first = true;
    for (const std::string &name : panel_order) {
        std::ifstream in(checkpoint_path(name));
        std::ostringstream raw;
        raw << in.rdbuf();
        if (!first) {
            parts << '\n';
        }
        first = false;
        parts << name << ".chk=" << fnv_hex(raw.str());
    }
    return fnv_hex(parts.str());
}

}  // namespace journal
}  // namespace vlt
