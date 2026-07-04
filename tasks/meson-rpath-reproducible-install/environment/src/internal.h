#ifndef CAPSULE_INTERNAL_H
#define CAPSULE_INTERNAL_H

#include <stddef.h>
#include <capsule.h>

struct capsule_view {
    int weight;
    int bucket;
    const char *profile;
};

int cap_fold_ascii(const char *text);
int cap_clamp_bucket(int weight);
void cap_write_pair(char *buffer, size_t length, const char *name, const char *value);
struct capsule_view cap_view_from_text(const char *text);

#endif
