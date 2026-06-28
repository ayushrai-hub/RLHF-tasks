#!/bin/bash
set -euo pipefail

ROOT="/app/environment"

python3 <<'PY'
from pathlib import Path

root = Path("/app/environment")

edge = root / "q4/edge_scan.c"
text = edge.read_text()
anchor = (
    '  snprintf(rel, sizeof rel, "%s/libcore/widget.h", root);\n'
    '  push_dep(out, rel);\n'
    '  if (strstr(root, "app_v1")) {'
)
insert = (
    '  char gen_slot[512];\n'
    '  snprintf(gen_slot, sizeof gen_slot, "%s/var/gen/version_slot.h", g->root);\n'
    '  push_dep(out, gen_slot);\n'
)
if "version_slot.h" not in text and anchor in text:
    text = text.replace(anchor, insert + '  if (strstr(root, "app_v1")) {', 1)
    edge.write_text(text)

(root / "w7/stamp_lane.c").write_text(
    """#include "lib_iface.h"

int phase_b(const struct stat *src, const struct stat *obj, int mode) {
  (void)mode;
  if (!src || !obj) {
    return 0;
  }
  if (obj->st_size == 0) {
    return 0;
  }
  if (src->st_mtime < obj->st_mtime) {
    return 1;
  }
  if (src->st_mtime == obj->st_mtime) {
    return 0;
  }
  return 0;
}
"""
)

(root / "p2/slot_lane.c").write_text(
    '''#include "lib_iface.h"

#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

int reconcile_c(struct slot_tbl *t, uint32_t gen, const char *blob_path) {
  if (!t || !blob_path) {
    return -1;
  }
  struct stat hdr_st;
  struct stat blob_st;
  if (stat(tb_gen_hdr(), &hdr_st) != 0) {
    return 0;
  }
  if (stat(blob_path, &blob_st) != 0) {
    return 0;
  }
  uint32_t hdr_gen = (uint32_t)((hdr_st.st_mtime ^ hdr_st.st_size) & 0xffffffffu);
  if (gen != hdr_gen) {
    return 0;
  }
  uint32_t live = (uint32_t)((blob_st.st_mtime ^ blob_st.st_size) & 0xffffffffu);
  for (int i = 0; i < t->n; i++) {
    if (strcmp(t->blobs[i], blob_path) == 0) {
      if (t->gen[i] == hdr_gen && t->gen[i] == live) {
        return 1;
      }
      t->gen[i] = hdr_gen;
      return 0;
    }
  }
  if (t->n < TB_MAX_SLOTS) {
    snprintf(t->blobs[t->n], TB_ROOT_LEN, "%s", blob_path);
    t->gen[t->n] = hdr_gen;
    t->n++;
  }
  return 0;
}
'''
)

ring = root / "k9/cache_ring.c"
ring_text = ring.read_text()
ring_text = ring_text.replace(
    """  (void)gen;
  for (int i = 0; i < g_ring_n; i++) {
    if (strcmp(g_ring[i].blob, blob) == 0) {
      return 1;
    }
  }""",
    """  for (int i = 0; i < g_ring_n; i++) {
    if (strcmp(g_ring[i].blob, blob) == 0 && g_ring[i].gen == gen) {
      return 1;
    }
  }""",
)
ring.write_text(ring_text)

core = root / "host/bld_core.c"
core_text = core.read_text()
skip_block = """  if (!force && strstr(src_rel, "widget.c")) {
    struct stat st_obj_only;
    if (stat(obj, &st_obj_only) == 0) {
      journal_line("skip", src_rel);
      return 0;
    }
  }
"""
if skip_block in core_text:
    core_text = core_text.replace(skip_block, "", 1)

hdr_check = """  return tb_mtime_fresh(&st_src, &st_obj) == 0;
}"""
hdr_replacement = """  if (tb_mtime_fresh(&st_src, &st_obj) == 0) {
    return 1;
  }
  if (strstr(src, "main.c") || strstr(src, "aux.c") || strstr(src, "widget.c")) {
    struct stat st_hdr;
    if (stat(tb_gen_hdr(), &st_hdr) == 0) {
#if defined(__linux__)
      if (st_obj.st_mtim.tv_sec < st_hdr.st_mtim.tv_sec ||
          (st_obj.st_mtim.tv_sec == st_hdr.st_mtim.tv_sec &&
           st_obj.st_mtim.tv_nsec < st_hdr.st_mtim.tv_nsec)) {
        return 1;
      }
#else
      if (st_obj.st_mtime < st_hdr.st_mtime) {
        return 1;
      }
#endif
    }
  }
  return 0;
}"""
if hdr_check in core_text:
    core_text = core_text.replace(hdr_check, hdr_replacement, 1)

render_anchor = "  tb_scan_deps_for_dirty();\n  return 0;\n}"
render_replacement = (
    "  tb_scan_deps_for_dirty();\n  tb_ring_clear();\n  return 0;\n}"
)
if render_anchor in core_text:
    core_text = core_text.replace(render_anchor, render_replacement, 1)
core.write_text(core_text)
PY

cmake --build /app/environment/_build --target clean
cmake --build /app/environment/_build --target bld_host trace_host
/app/environment/bin/trace_host /app/environment/data/run_plan.json
