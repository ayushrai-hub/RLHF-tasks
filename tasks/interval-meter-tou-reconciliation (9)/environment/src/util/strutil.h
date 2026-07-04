#ifndef TOU_STRUTIL_H
#define TOU_STRUTIL_H

#include <stddef.h>

void trim_newline(char *line);
int starts_with(const char *s, const char *prefix);
int parse_double_field(const char *field, double *out);

#endif
