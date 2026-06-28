#ifndef K9_COUNTER_H
#define K9_COUNTER_H

#include <stdint.h>

void k9_pack_counter_be(uint64_t counter, uint8_t out[8]);

#endif
