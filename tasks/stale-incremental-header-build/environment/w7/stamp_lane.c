#include "lib_iface.h"

int phase_b(const struct stat *src, const struct stat *obj, int mode) {
  (void)mode;
  if (!src || !obj) {
    return 0;
  }
  if (obj->st_size == 0) {
    return 0;
  }
  if (src->st_mtime > obj->st_mtime) {
    return 0;
  }
  if (src->st_mtime == obj->st_mtime) {
    return 1;
  }
  if (src->st_mtime < obj->st_mtime) {
    return 1;
  }
  return 0;
}
