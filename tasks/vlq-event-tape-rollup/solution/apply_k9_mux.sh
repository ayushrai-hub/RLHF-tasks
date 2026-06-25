#!/bin/bash
set -euo pipefail
cat > /app/environment/w33/k9_mux.cpp <<'CPP'
#include "digest.h"
#include "types.h"
#include <sstream>

namespace vlt {

std::string k9_row_serial(const PanelRun &run) {
    std::ostringstream os;
    os << run.name << '|' << run.event_count << '|' << run.tag_span;
    for (const auto &cell : run.answers) {
        if (cell.op == "fold") {
            os << "|fold|" << cell.from << '|' << cell.to << '|' << cell.value;
        } else if (cell.op == "peek") {
            os << "|peek|" << cell.at << '|' << cell.value;
        } else {
            os << "|tally|" << cell.mask << '|' << cell.value;
        }
    }
    return os.str();
}

std::string k9_panel_digest(const PanelRun &run) {
    return fnv_hex(k9_row_serial(run));
}

}  // namespace vlt

CPP
