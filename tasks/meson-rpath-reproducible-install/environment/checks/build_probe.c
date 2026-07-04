#include <capsule.h>
#include <string.h>

int main(void) {
    if (capsule_weight("Acme-Crate") <= 0) {
        return 1;
    }
    if (capsule_bucket_for("Acme-Crate") <= 0) {
        return 2;
    }
    if (strlen(capsule_package_id()) == 0) {
        return 3;
    }
    return 0;
}
