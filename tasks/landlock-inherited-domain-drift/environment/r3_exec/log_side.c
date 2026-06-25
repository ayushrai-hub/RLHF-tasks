#include <stdio.h>

int log_side_export(const char *tag, char *buf, size_t cap)
{
    (void)tag;
    if (buf == NULL || cap < 8) {
        return -1;
    }
    (void)snprintf(buf, cap, "legacy");
    return 0;
}
