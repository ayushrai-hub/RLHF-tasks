#include "parse_path.h"

#include <ctype.h>
#include <stdio.h>
#include <string.h>

int pp_token_count(const char *line)
{
    int count = 0;
    int in_tok = 0;
    for (const char *p = line; *p; p++) {
        if (isspace((unsigned char)*p)) {
            in_tok = 0;
        } else if (!in_tok) {
            in_tok = 1;
            count++;
        }
    }
    return count;
}

int pp_env_value(const char *path, const char *key, char *out, size_t cap)
{
    FILE *f = fopen(path, "r");
    if (f == NULL) {
        return -1;
    }
    char line[512];
    size_t klen = strlen(key);
    while (fgets(line, sizeof(line), f) != NULL) {
        if (strncmp(line, key, klen) == 0 && line[klen] == '=') {
            const char *val = line + klen + 1;
            size_t n = strcspn(val, "\r\n");
            if (n >= cap) {
                fclose(f);
                return -1;
            }
            memcpy(out, val, n);
            out[n] = '\0';
            fclose(f);
            return 0;
        }
    }
    fclose(f);
    return -1;
}
