#include "lib_iface.h"

#include <stdio.h>
#include <string.h>

extern int op_a(struct graph_ctx *g, const char *root, struct edge_buf *out);

int tb_emit_dep_audit(const char *target, const char *out_path) {
  if (!target || !out_path) {
    return -1;
  }
  char root[512];
  snprintf(root, sizeof root, "%s", tb_env_root());
  if (strcmp(target, "app_v1") == 0) {
    snprintf(root, sizeof root, "%s/app_v1", tb_env_root());
  } else if (strcmp(target, "app_v2") == 0) {
    snprintf(root, sizeof root, "%s/app_v2", tb_env_root());
  } else {
    return -1;
  }
  struct graph_ctx g;
  struct edge_buf edges;
  snprintf(g.root, sizeof g.root, "%s", tb_env_root());
  if (op_a(&g, root, &edges) != 0) {
    return -1;
  }
  FILE *f = fopen(out_path, "w");
  if (!f) {
    return -1;
  }
  fputs("{\"target\":\"", f);
  fputs(target, f);
  fputs("\",\"paths\":[", f);
  for (int i = 0; i < edges.n; i++) {
    if (i) {
      fputc(',', f);
    }
    fputc('"', f);
    for (const char *p = edges.paths[i]; *p; p++) {
      if (*p == '"' || *p == '\\') {
        fputc('\\', f);
      }
      fputc(*p, f);
    }
    fputc('"', f);
  }
  fputs("]}\n", f);
  fclose(f);
  return 0;
}
