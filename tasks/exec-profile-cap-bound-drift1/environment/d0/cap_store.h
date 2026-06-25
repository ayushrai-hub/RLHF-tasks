#ifndef CAP_STORE_H
#define CAP_STORE_H

#include "cap_layout.h"

int cap_store_load(void);
int cap_store_save(void);
int cap_store_clear(void);
int cap_store_count(void);
int cap_store_get(int index, cap_row_t *row);
int cap_store_upsert(const cap_row_t *row);
int cap_store_find(const char *round, const char *actor, const char *mark, cap_row_t *row);

#endif
