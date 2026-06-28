#ifndef K9_MAC_H
#define K9_MAC_H

#include <stddef.h>

int k9_mac_input_from_token(const char *header, const char *payload,
                            char *out, size_t cap, size_t *out_len);

#endif
