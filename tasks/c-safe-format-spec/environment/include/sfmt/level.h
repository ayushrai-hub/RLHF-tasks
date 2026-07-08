#ifndef SFMT_LEVEL_H
#define SFMT_LEVEL_H

typedef enum {
    SF_LEVEL_DEBUG,
    SF_LEVEL_INFO,
    SF_LEVEL_WARN,
    SF_LEVEL_ERROR
} sf_level;

const char *sf_level_name(sf_level level);

int sf_level_parse(const char *s, sf_level *out);

#endif
