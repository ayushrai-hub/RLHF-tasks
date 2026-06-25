#!/bin/bash
set -euo pipefail
cat > /app/environment/common/stage_seal.cpp <<'CPP'
#include "types.h"
#include "digest.h"
#include "vlt_journal.h"
#include <sstream>
#include <vector>

namespace vlt {
std::string k9_row_serial(const PanelRun &run);
}

namespace vlt {
namespace stage {

std::string row_serial(const PanelRun &run) {
    return k9_row_serial(run);
}

std::string panel_digest(const PanelRun &run) {
    return fnv_hex(k9_row_serial(run));
}

std::string campaign_digest(int schema_version, const std::string &campaign_id,
                            const std::vector<PanelRun> &panels,
                            const std::vector<std::string> &panel_order) {
    std::ostringstream top;
    top << schema_version << '|' << campaign_id;
    for (const auto &run : panels) {
        top << '\n' << k9_row_serial(run);
    }
    top << '\n' << journal::tail_binding(panel_order);
    return fnv_hex(top.str());
}

void write_panel_checkpoint(const std::string &panel_name, const std::string &tape_fp,
                            const std::string &row_digest) {
    journal::write_checkpoint(panel_name, tape_fp, row_digest);
}

void reset_journal() {
    journal::clear_all();
}

std::string journal_tail(const std::vector<std::string> &panel_order) {
    return journal::tail_binding(panel_order);
}

}  // namespace stage
}  // namespace vlt

CPP
