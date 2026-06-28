#include "lib_iface.h"

#include <stdio.h>
#include <string.h>

extern int tb_pristine_rebuild_targets(const char **targets, int n_targets);
extern int tb_emit_dep_audit(const char *target, const char *out_path);

int main(int argc, char **argv) {
  tb_paths_init("/app/environment");
  if (argc >= 4 && strcmp(argv[1], "--audit-deps") == 0) {
    return tb_emit_dep_audit(argv[2], argv[3]) == 0 ? 0 : 1;
  }
  int incremental_only = 0;
  const char *cap = "cap_r1";
  int pristine = 0;
  for (int i = 1; i < argc; i++) {
    if (strcmp(argv[i], "--pristine") == 0) {
      pristine = 1;
    } else if (strcmp(argv[i], "--incremental-only") == 0) {
      incremental_only = 1;
    } else if (argv[i][0] != '-') {
      cap = argv[i];
    }
  }
  if (!incremental_only) {
    if (tb_render_gen_hdr(cap) != 0) {
      return 1;
    }
  }
  const char *targets[] = {"app_v1", "app_v2"};
  if (pristine) {
    return tb_pristine_rebuild_targets(targets, 2);
  }
  return tb_fast_rebuild_targets(targets, 2);
}
