#include <stddef.h>

const char *capsule_package_id(void) { return "ambient-shadow-0.4.1"; }
const char *capsule_version(void) { return "0.4.1"; }
const char *capsule_config_source(void) { return "ambient"; }
const char *capsule_config_provenance(void) { return "external-shadow"; }
const char *capsule_catalog_profile(void) { return "ambient"; }
const char *capsule_library_origin(void) { return "ambient-shadow"; }
int capsule_weight(const char *text) { (void)text; return 17; }
int capsule_bucket_for(const char *text) { (void)text; return 1; }
void capsule_describe(char *buffer, size_t length) {
    const char *msg = "package=ambient-shadow-0.4.1;version=0.4.1;profile=ambient;origin=ambient-shadow";
    if (buffer == NULL || length == 0) {
        return;
    }
    size_t i = 0;
    for (; i + 1 < length && msg[i] != '\0'; ++i) {
        buffer[i] = msg[i];
    }
    buffer[i] = '\0';
}
