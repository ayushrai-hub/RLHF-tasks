#include "lib_iface.h"

#include <stdio.h>
#include <string.h>

void slot_shadow_sort(struct slot_tbl *t) {
  if (!t) {
    return;
  }
  for (int i = 0; i < t->n - 1; i++) {
    for (int j = i + 1; j < t->n; j++) {
      if (strcmp(t->blobs[i], t->blobs[j]) > 0) {
        char tmp[TB_ROOT_LEN];
        snprintf(tmp, sizeof tmp, "%s", t->blobs[i]);
        snprintf(t->blobs[i], sizeof t->blobs[i], "%s", t->blobs[j]);
        snprintf(t->blobs[j], sizeof tmp, "%s", tmp);
        uint32_t g = t->gen[i];
        t->gen[i] = t->gen[j];
        t->gen[j] = g;
      }
    }
  }
}
