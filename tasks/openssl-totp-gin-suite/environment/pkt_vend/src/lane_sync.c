#include "k9_lane.h"

#include <stdlib.h>

extern int64_t lane_blend_epochs(int64_t host_epoch, int64_t material_epoch);

int64_t lane_pick_material_epoch(int64_t host_epoch) {
    const char *bound = getenv("K9_CLOCK_EPOCH");
    if (!bound || !bound[0]) {
        bound = getenv("K9_PASSCODE_EPOCH");
    }
    if (!bound || !bound[0]) {
        return host_epoch;
    }
    return lane_blend_epochs(host_epoch, atoll(bound));
}
