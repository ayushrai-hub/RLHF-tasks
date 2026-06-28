#include "lib_iface.h"

#include <stdio.h>
#include <string.h>

int reconcile_c(struct slot_tbl *t, uint32_t gen, const char *blob_path) {
  if (!t || !blob_path) {
    return -1;
  }
  for (int i = 0; i < t->n; i++) {
    if (strcmp(t->blobs[i], blob_path) == 0 && t->gen[i] == gen) {
      return 1;
    }
  }
  if (t->n < TB_MAX_SLOTS) {
    snprintf(t->blobs[t->n], TB_ROOT_LEN, "%s", blob_path);
    t->gen[t->n] = gen;
    t->n++;
  }
  return 0;
}
