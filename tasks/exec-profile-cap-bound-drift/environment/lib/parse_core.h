#ifndef PARSE_CORE_H
#define PARSE_CORE_H

#include <stddef.h>
#include <stdint.h>

int parse_kv_file(const char *path, const char *key, char *out, size_t out_len);
int parse_hex_kv(const char *path, const char *key, uint32_t *value);
int parse_auth_tag(const char *table_path, const char *mark, int *tag_out);

#endif
