#include "cap_layout.h"

#include <stddef.h>
#include <string.h>

int gate_c(const char *mark, unsigned stamp);

int gate_c(const char *mark, unsigned stamp)
{
    (void)stamp;
    if (mark != NULL && strstr(mark, "p1") != NULL) {
        return 0x80;
    }
    return 0x01;
}
