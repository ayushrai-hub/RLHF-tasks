#include "dig01.h"

#include <stdint.h>
#include <string.h>

int gate_k3(const char *main_elf, char **so_list, size_t nso, uint32_t *violations)
{
    if (!main_elf || !violations) {
        return -1;
    }
    char main_hex[32];
    if (dig01_digest_hex(main_elf, main_hex, sizeof(main_hex)) != 0) {
        return -2;
    }
    uint32_t count = 0;
    for (size_t i = 0; so_list && i + 1 < nso; i++) {
        char dep_hex[32];
        if (dig01_digest_hex(so_list[i], dep_hex, sizeof(dep_hex)) != 0) {
            continue;
        }
        if (strcmp(main_hex, dep_hex) != 0) {
            count++;
        }
    }
    *violations = count;
    return 0;
}
