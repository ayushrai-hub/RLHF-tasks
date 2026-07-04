#include <capsule.h>
#include <stdio.h>

int main(void) {
    printf("consumer_package_id=%s\n", capsule_package_id());
    printf("consumer_provenance=%s\n", capsule_config_provenance());
    printf("consumer_origin=%s\n", capsule_library_origin());
    return 0;
}
