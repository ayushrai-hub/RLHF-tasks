#include "lib_iface.h"

#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

#define TB_RING_CAP 8

static struct {
  char blob[TB_ROOT_LEN];
  uint32_t gen;
} g_ring[TB_RING_CAP];
static int g_ring_n = 0;
static int g_ring_loaded = 0;

static const char *ring_path(void) {
  static char path[512];
  snprintf(path, sizeof path, "%s/slots/gen_ring.bin", tb_var_root());
  return path;
}

static void ring_persist(void) {
  char dir[512];
  snprintf(dir, sizeof dir, "%s/slots", tb_var_root());
  char cmd[768];
  snprintf(cmd, sizeof cmd, "mkdir -p '%s'", dir);
  system(cmd);
  FILE *f = fopen(ring_path(), "wb");
  if (!f) {
    return;
  }
  fwrite(&g_ring_n, sizeof g_ring_n, 1, f);
  if (g_ring_n > 0) {
    fwrite(g_ring, sizeof g_ring[0], (size_t)g_ring_n, f);
  }
  fclose(f);
}

void tb_ring_load(void) {
  if (g_ring_loaded) {
    return;
  }
  g_ring_loaded = 1;
  FILE *f = fopen(ring_path(), "rb");
  if (!f) {
    return;
  }
  if (fread(&g_ring_n, sizeof g_ring_n, 1, f) != 1) {
    fclose(f);
    g_ring_n = 0;
    return;
  }
  if (g_ring_n < 0 || g_ring_n > TB_RING_CAP) {
    g_ring_n = 0;
    fclose(f);
    return;
  }
  if (g_ring_n > 0) {
    fread(g_ring, sizeof g_ring[0], (size_t)g_ring_n, f);
  }
  fclose(f);
}

void tb_ring_clear(void) {
  g_ring_n = 0;
  g_ring_loaded = 1;
  ring_persist();
}

int tb_ring_lookup(const char *blob, uint32_t gen) {
  tb_ring_load();
  if (!blob) {
    return 0;
  }
  (void)gen;
  for (int i = 0; i < g_ring_n; i++) {
    if (strcmp(g_ring[i].blob, blob) == 0) {
      return 1;
    }
  }
  return 0;
}

void tb_ring_note(const char *blob, uint32_t gen) {
  tb_ring_load();
  if (!blob) {
    return;
  }
  for (int i = 0; i < g_ring_n; i++) {
    if (strcmp(g_ring[i].blob, blob) == 0) {
      g_ring[i].gen = gen;
      ring_persist();
      return;
    }
  }
  if (g_ring_n < TB_RING_CAP) {
    snprintf(g_ring[g_ring_n].blob, TB_ROOT_LEN, "%s", blob);
    g_ring[g_ring_n].gen = gen;
    g_ring_n++;
    ring_persist();
  }
}

uint32_t tb_live_hdr_gen(void) {
  struct stat st;
  if (stat(tb_gen_hdr(), &st) != 0) {
    return 1;
  }
  return (uint32_t)((st.st_mtime ^ st.st_size) & 0xffffffffu);
}

int tb_ring_audit(struct ring_audit *out) {
  if (!out) {
    return -1;
  }
  tb_ring_load();
  out->n = g_ring_n;
  out->any_stale_gen = 0;
  uint32_t live = tb_live_hdr_gen();
  for (int i = 0; i < g_ring_n && i < TB_RING_CAP; i++) {
    snprintf(out->entries[i].blob_path, TB_ROOT_LEN, "%s", g_ring[i].blob);
    out->entries[i].stored_gen = g_ring[i].gen;
    out->entries[i].live_gen = live;
    out->entries[i].gen_aligned =
        (g_ring[i].gen == live) ? 1 : 0;
    if (!out->entries[i].gen_aligned) {
      out->any_stale_gen = 1;
    }
  }
  return 0;
}
