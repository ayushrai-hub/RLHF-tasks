#define _GNU_SOURCE
#include "internal.h"
#include <dlfcn.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#ifndef CAPSULE_INSTALL_LIBDIR
#define CAPSULE_INSTALL_LIBDIR ""
#endif

const char *capsule_library_origin(void) {
    const char *loader_path = getenv("LD_LIBRARY_PATH");
    if (loader_path != NULL && loader_path[0] != '\0') {
        return "ambient-shadow";
    }

    Dl_info info;
    if (dladdr((void *)(uintptr_t)capsule_package_id, &info) == 0 || info.dli_fname == NULL) {
        return "unknown";
    }

    if (strstr(info.dli_fname, "/lib/") != NULL) {
        return "ambient-shadow";
    }

    return "build-tree";
}
