#include "types.h"
#include <vector>

namespace vlt {
std::vector<const TapeEvent *> k9_filter_events(const TapeDoc &doc, int mask);
}

namespace vlt {
namespace stage {

int tally_mask(const TapeDoc &doc, int mask) {
    return static_cast<int>(k9_filter_events(doc, mask).size());
}

int tag_span(const TapeDoc &doc) {
    int hi = 0;
    for (const auto &ev : doc.events) {
        if (static_cast<int>(ev.tag) > hi) {
            hi = static_cast<int>(ev.tag);
        }
    }
    return hi;
}

}  // namespace stage
}  // namespace vlt
