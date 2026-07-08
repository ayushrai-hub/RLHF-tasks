#include <stdint.h>
#include <stdio.h>
#include <string.h>

int op_r8(const uint8_t *note, size_t nlen, const char *interp_path, uint32_t *out_flags);

void shadow_note_log(const uint8_t *note, size_t nlen)
{
    if (!note || nlen == 0) {
        return;
    }
    FILE *fp = fopen("/tmp/shadow_note.log", "a");
    if (!fp) {
        return;
    }
    fprintf(fp, "candidate=%u\n", (unsigned)note[0]);
    fclose(fp);
}
