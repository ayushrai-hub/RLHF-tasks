#include "lib_iface.h"

#include <stdio.h>
#include <string.h>

extern int op_a(struct graph_ctx *g, const char *root, struct edge_buf *out);
extern void tb_note_widget_dirty(void);

void tb_scan_deps_for_dirty(void) {
  struct graph_ctx g;
  struct edge_buf edges;
  snprintf(g.root, sizeof g.root, "%s", tb_env_root());
  op_a(&g, g.root, &edges);
  for (int i = 0; i < edges.n; i++) {
    if (strstr(edges.paths[i], "version_slot.h")) {
      tb_note_widget_dirty();
      return;
    }
  }
}
