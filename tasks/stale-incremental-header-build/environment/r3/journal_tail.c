#include "lib_iface.h"

#include <stdio.h>
#include <string.h>

static int tail_has_skip(const char *src_rel) {
  char log_path[512];
  snprintf(log_path, sizeof log_path, "%s/stats/compile.log", tb_var_root());
  FILE *f = fopen(log_path, "r");
  if (!f) {
    return 0;
  }
  char line[512];
  int saw = 0;
  while (fgets(line, sizeof line, f)) {
    char action[32];
    char src[256];
    char mode[32];
    if (sscanf(line, "%31s\t%255s\t%31s", action, src, mode) != 3) {
      continue;
    }
    if (strcmp(action, "skip") == 0 && strstr(src, src_rel)) {
      saw = 1;
    }
  }
  fclose(f);
  return saw;
}

int tb_journal_surface(struct journal_surface *out, const char *src_rel) {
  if (!out || !src_rel) {
    return -1;
  }
  snprintf(out->source_rel, sizeof out->source_rel, "%s", src_rel);
  out->last_action_skip = tail_has_skip(src_rel) ? 1 : 0;
  return 0;
}
