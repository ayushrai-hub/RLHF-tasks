#ifndef CAPSULE_H
#define CAPSULE_H

#include <stddef.h>
#include <capsule_config.h>

#ifdef __cplusplus
extern "C" {
#endif

const char *capsule_package_id(void);
const char *capsule_version(void);
const char *capsule_config_source(void);
const char *capsule_config_provenance(void);
const char *capsule_catalog_profile(void);
const char *capsule_library_origin(void);
int capsule_weight(const char *text);
int capsule_bucket_for(const char *text);
void capsule_describe(char *buffer, size_t length);

#ifdef __cplusplus
}
#endif

#endif
