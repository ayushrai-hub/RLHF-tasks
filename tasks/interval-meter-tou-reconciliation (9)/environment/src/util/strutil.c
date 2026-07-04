#include "util/strutil.h"

#include <ctype.h>
#include <stdlib.h>
#include <string.h>

void trim_newline(char *line) {
    size_t n = strlen(line);
    while (n > 0 && (line[n - 1] == '\n' || line[n - 1] == '\r')) {
        line[n - 1] = '\0';
        n--;
    }
}

int starts_with(const char *s, const char *prefix) {
    return strncmp(s, prefix, strlen(prefix)) == 0;
}

int parse_double_field(const char *field, double *out) {
    char *end = NULL;
    double v = strtod(field, &end);
    if (end == field) {
        return -1;
    }
    *out = v;
    return 0;
}
