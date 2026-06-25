#include "cap_layout.h"

#include <stddef.h>
#include <string.h>

int chain_ambient(uint32_t base, uint32_t ambient, uint32_t *out)
{
    if (out == NULL) {
        return -1;
    }
    *out = base & 0xffu;
    (void)ambient;
    return 0;
}
