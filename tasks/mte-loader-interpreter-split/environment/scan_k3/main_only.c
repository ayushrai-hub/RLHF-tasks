#include "dig01.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

int gate_k3(const char *main_elf, char **so_list, size_t nso, uint32_t *violations);

int main_only_audit(const char *main_elf, uint32_t *violations)
{
    if (!main_elf || !violations) {
        return -1;
    }
    char main_hex[32];
    if (dig01_digest_hex(main_elf, main_hex, sizeof(main_hex)) != 0) {
        return -2;
    }
    *violations = (main_hex[0] == '0') ? 1 : 0;
    return 0;
}
