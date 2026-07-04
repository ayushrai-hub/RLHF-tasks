#include <capsule.h>
#include <stdio.h>

int main(int argc, char **argv) {
    const char *value = argc > 1 ? argv[1] : "capsule";
    printf("input=%s\n", value);
    printf("weight=%d\n", capsule_weight(value));
    printf("bucket=%d\n", capsule_bucket_for(value));
    printf("package_id=%s\n", capsule_package_id());
    return 0;
}
