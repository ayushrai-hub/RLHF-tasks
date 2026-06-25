#include "digest.h"
#include "types.h"
#include <sstream>

namespace vlt {

std::string k9_row_serial(const PanelRun &run) {
    std::ostringstream os;
    os << run.tag_span << '|' << run.event_count << '|' << run.name;
    for (const auto &cell : run.answers) {
        os << '|' << cell.value;
    }
    return os.str();
}

std::string k9_panel_digest(const PanelRun &run) {
    return fnv_hex(k9_row_serial(run));
}

}  // namespace vlt
