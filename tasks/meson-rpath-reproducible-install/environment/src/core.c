#include "internal.h"
#include <stdio.h>

int capsule_weight(const char *text) {
    return cap_fold_ascii(text);
}

int capsule_bucket_for(const char *text) {
    return cap_clamp_bucket(capsule_weight(text));
}

void capsule_describe(char *buffer, size_t length) {
    if (buffer == NULL || length == 0) {
        return;
    }
    snprintf(
        buffer,
        length,
        "package=%s;version=%s;profile=%s;origin=%s",
        capsule_package_id(),
        capsule_version(),
        capsule_catalog_profile(),
        capsule_library_origin()
    );
}
