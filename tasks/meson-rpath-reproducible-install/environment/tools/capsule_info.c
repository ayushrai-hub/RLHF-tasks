#include <capsule.h>
#include <stdio.h>

int main(void) {
    char description[256];
    capsule_describe(description, sizeof(description));
    printf("compiled_package_id=%s\n", CAPSULE_PACKAGE_ID);
    printf("compiled_version=%s\n", CAPSULE_VERSION);
    printf("compiled_source=%s\n", CAPSULE_CONFIG_SOURCE);
    printf("compiled_provenance=%s\n", CAPSULE_CONFIG_PROVENANCE);
    printf("linked_package_id=%s\n", capsule_package_id());
    printf("linked_version=%s\n", capsule_version());
    printf("linked_source=%s\n", capsule_config_source());
    printf("linked_provenance=%s\n", capsule_config_provenance());
    printf("linked_origin=%s\n", capsule_library_origin());
    printf("description=%s\n", description);
    return 0;
}
