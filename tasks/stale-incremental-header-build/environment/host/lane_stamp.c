#include "lib_iface.h"

extern int phase_b(const struct stat *src, const struct stat *obj, int mode);

int tb_mtime_fresh(const struct stat *src, const struct stat *obj) {
  return phase_b(src, obj, 0);
}
