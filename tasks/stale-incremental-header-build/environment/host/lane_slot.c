#include "lib_iface.h"

extern int reconcile_c(struct slot_tbl *t, uint32_t gen, const char *blob_path);

int tb_slot_reuse_ok(struct slot_tbl *t, uint32_t gen, const char *blob_path) {
  return reconcile_c(t, gen, blob_path);
}
