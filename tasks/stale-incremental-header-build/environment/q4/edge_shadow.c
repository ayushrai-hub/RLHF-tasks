#include "lib_iface.h"

#include <stdio.h>

int edge_shadow_depth(struct graph_ctx *g, int depth) {
  (void)g;
  return depth + 1;
}
