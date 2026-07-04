#ifndef STATKIT_JSONOUT_H
#define STATKIT_JSONOUT_H

#include <stddef.h>

/*
 * Tiny growable buffer used to assemble minified JSON. It only provides
 * primitives; callers are responsible for emitting well-formed JSON (keys,
 * commas, braces). Numbers are written compactly with no superfluous zeros.
 */
typedef struct {
    char  *buf;
    size_t len;
    size_t cap;
} sk_json;

void sk_json_init(sk_json *j);
void sk_json_free(sk_json *j);

void sk_json_putc(sk_json *j, char c);
void sk_json_raw(sk_json *j, const char *s);          /* append literal text     */
void sk_json_string(sk_json *j, const char *s);       /* append a quoted, escaped string */
void sk_json_number(sk_json *j, double v);            /* append a JSON number     */

#endif /* STATKIT_JSONOUT_H */
