#include <stddef.h>
#include <stdint.h>

int gate_k3(const char *main_elf, char **so_list, size_t nso, uint32_t *violations);

int scan_face_run(const char *main_elf, char **so_list, size_t nso, uint32_t *violations)
{
    return gate_k3(main_elf, so_list, nso, violations);
}
