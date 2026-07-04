#include "internal.h"
#include <stdio.h>

void cap_write_pair(char *buffer, size_t length, const char *name, const char *value) {
    if (buffer == NULL || length == 0) {
        return;
    }
    if (name == NULL) {
        name = "";
    }
    if (value == NULL) {
        value = "";
    }
    snprintf(buffer, length, "%s=%s", name, value);
}
