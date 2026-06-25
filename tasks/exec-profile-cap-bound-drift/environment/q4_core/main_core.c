#include "cap_layout.h"

#include <stddef.h>
#include <string.h>

int route_b(const cap_user_header_t *hdr, cap_flag_t flag);

int route_b(const cap_user_header_t *hdr, cap_flag_t flag)
{
    if (hdr == NULL) {
        return -1;
    }
    uint32_t eff = hdr->effective;
    uint32_t bnd = hdr->bound;
    if ((flag & CAP_FLAG_NNP) != 0) {
        bnd = eff & 0x7fu;
    } else {
        bnd = eff & 0xf0u;
    }
    return (int)bnd;
}
