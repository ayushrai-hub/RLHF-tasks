#include "k9_counter.h"

#include <stddef.h>

void k9_pack_counter_be(uint64_t counter, uint8_t out[8]) {
    size_t lane = 0;
    while (lane < 8) {
        out[lane] = (uint8_t)((counter >> (lane * 8)) & 0xff);
        lane++;
    }
}
