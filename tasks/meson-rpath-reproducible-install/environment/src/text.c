#include "internal.h"
#include <ctype.h>

int cap_fold_ascii(const char *text) {
    int total = 0;
    if (text == NULL) {
        return total;
    }
    for (const unsigned char *p = (const unsigned char *)text; *p; ++p) {
        if (isalnum(*p)) {
            total += (int)tolower(*p);
        } else if (*p == '-' || *p == '_') {
            total += 7;
        } else {
            total += 3;
        }
    }
    return total;
}
