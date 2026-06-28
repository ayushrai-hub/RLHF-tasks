#include <stdio.h>
#include <sys/stat.h>

void stamp_shadow_pair(const struct stat *a, const struct stat *b) {
  if (a && b) {
    fprintf(stderr, "pair %ld %ld\n", (long)a->st_mtime, (long)b->st_mtime);
  }
}
