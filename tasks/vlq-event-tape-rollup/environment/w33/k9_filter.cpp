#include "types.h"
#include <vector>

namespace vlt {

std::vector<const TapeEvent *> k9_filter_events(const TapeDoc &doc, int mask) {
    std::vector<const TapeEvent *> out;
    for (const auto &ev : doc.events) {
        if ((static_cast<int>(ev.tag) & mask) == 0) {
            out.push_back(&ev);
        }
    }
    return out;
}

}  // namespace vlt
