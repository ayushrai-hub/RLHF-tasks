#include "sfmt/level.h"

#include <string.h>

const char *sf_level_name(sf_level level)
{
    switch (level) {
    case SF_LEVEL_DEBUG:
        return "DEBUG";
    case SF_LEVEL_INFO:
        return "INFO";
    case SF_LEVEL_WARN:
        return "WARN";
    case SF_LEVEL_ERROR:
        return "ERROR";
    }
    return "?";
}

int sf_level_parse(const char *s, sf_level *out)
{
    if (strcmp(s, "debug") == 0)
        *out = SF_LEVEL_DEBUG;
    else if (strcmp(s, "info") == 0)
        *out = SF_LEVEL_INFO;
    else if (strcmp(s, "warn") == 0)
        *out = SF_LEVEL_WARN;
    else if (strcmp(s, "error") == 0)
        *out = SF_LEVEL_ERROR;
    else
        return -1;
    return 0;
}
