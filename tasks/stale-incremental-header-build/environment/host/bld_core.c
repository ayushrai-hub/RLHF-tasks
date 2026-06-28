#include "lib_iface.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int g_widget_dirty = 0;
static char g_compile_mode[16] = "fast";

static void journal_line(const char *action, const char *src_rel) {
  char log_path[512];
  snprintf(log_path, sizeof log_path, "%s/stats/compile.log", tb_var_root());
  char parent[512];
  snprintf(parent, sizeof parent, "%s/stats", tb_var_root());
  char cmd[768];
  snprintf(cmd, sizeof cmd, "mkdir -p '%s'", parent);
  system(cmd);
  FILE *f = fopen(log_path, "a");
  if (!f) {
    return;
  }
  fprintf(f, "%s\t%s\t%s\n", action, src_rel, g_compile_mode);
  fclose(f);
}

void tb_compile_journal_reset(void) {
  char log_path[512];
  snprintf(log_path, sizeof log_path, "%s/stats/compile.log", tb_var_root());
  remove(log_path);
}

void tb_compile_journal_set_mode(const char *mode) {
  if (mode) {
    snprintf(g_compile_mode, sizeof g_compile_mode, "%s", mode);
  }
}

void tb_note_widget_dirty(void) {
  g_widget_dirty = 1;
}

static int run_cmd(const char *cmd) {
  if (system(cmd) != 0) {
    return -1;
  }
  return 0;
}

int tb_render_gen_hdr(const char *cap_value) {
  char in_path[512];
  char out_path[512];
  snprintf(in_path, sizeof in_path, "%s/data/gen/version_slot.h.in", tb_env_root());
  snprintf(out_path, sizeof out_path, "%s", tb_gen_hdr());
  char cmd[1024];
  snprintf(cmd, sizeof cmd, "mkdir -p $(dirname '%s')", out_path);
  if (run_cmd(cmd) != 0) {
    return -1;
  }
  FILE *in = fopen(in_path, "r");
  FILE *out = fopen(out_path, "w");
  if (!in || !out) {
    if (in) {
      fclose(in);
    }
    if (out) {
      fclose(out);
    }
    return -1;
  }
  char line[256];
  while (fgets(line, sizeof line, in)) {
    char *at = strstr(line, "@CAP@");
    if (at) {
      *at = '\0';
      fputs(line, out);
      fputs(cap_value, out);
      fputs(at + 5, out);
    } else {
      fputs(line, out);
    }
  }
  fclose(in);
  fclose(out);
  tb_scan_deps_for_dirty();
  return 0;
}

static int ensure_dir(const char *path) {
  char cmd[768];
  snprintf(cmd, sizeof cmd, "mkdir -p '%s'", path);
  return run_cmd(cmd);
}

static int needs_rebuild(const char *src, const char *obj) {
  struct stat st_src;
  struct stat st_obj;
  if (stat(src, &st_src) != 0) {
    return 1;
  }
  if (stat(obj, &st_obj) != 0) {
    return 1;
  }
  return tb_mtime_fresh(&st_src, &st_obj) == 0;
}

int tb_compile_unit(const char *src_rel, const char *obj_rel, int force) {
  char src[512];
  char obj[512];
  snprintf(src, sizeof src, "%s/%s", tb_env_root(), src_rel);
  snprintf(obj, sizeof obj, "%s/%s", tb_var_root(), obj_rel);
  char objdir[512];
  snprintf(objdir, sizeof objdir, "%s", obj);
  {
    char parent[512];
    snprintf(parent, sizeof parent, "%s/objs", tb_var_root());
    ensure_dir(parent);
  }
  char *slash = strrchr(objdir, '/');
  if (slash) {
    *slash = '\0';
    ensure_dir(objdir);
  }
  if (!force && strstr(src_rel, "widget.c")) {
    struct stat st_obj_only;
    if (stat(obj, &st_obj_only) == 0) {
      journal_line("skip", src_rel);
      return 0;
    }
  }
  if (strstr(src_rel, "widget.c") && g_widget_dirty) {
    force = 1;
    g_widget_dirty = 0;
  }
  if (!force && !needs_rebuild(src, obj)) {
    journal_line("skip", src_rel);
    return 0;
  }
  journal_line("compile", src_rel);
  char cmd[1200];
  snprintf(
      cmd, sizeof cmd,
      "gcc -std=c11 -I'%s/libcore' -I'%s/var/gen' -c '%s' -o '%s'",
      tb_env_root(), tb_env_root(), src, obj);
  return run_cmd(cmd);
}

static uint32_t slot_gen_for(const char *bin_rel) {
  (void)bin_rel;
  struct stat st;
  if (stat(tb_gen_hdr(), &st) != 0) {
    return 1;
  }
  return (uint32_t)((st.st_mtime ^ st.st_size) & 0xffffffffu);
}

int tb_link_target(const char *target, const char *obj_rel, const char *bin_rel) {
  char obj[512];
  char bin[512];
  snprintf(obj, sizeof obj, "%s/%s", tb_var_root(), obj_rel);
  snprintf(bin, sizeof bin, "%s/%s", tb_var_root(), bin_rel);
  ensure_dir(tb_var_root());
  {
    char bindir[512];
    snprintf(bindir, sizeof bindir, "%s/bins", tb_var_root());
    ensure_dir(bindir);
  }
  struct slot_tbl tbl = {0};
  uint32_t gen = slot_gen_for(bin_rel);
  if (tb_ring_lookup(bin, gen) == 1) {
    struct stat st_bin;
    if (stat(bin, &st_bin) == 0) {
      return 0;
    }
  }
  if (tb_slot_reuse_ok(&tbl, gen, bin) == 1) {
    tb_ring_note(bin, gen);
    return 0;
  }
  char cmd[1400];
  if (strcmp(target, "app_v1") == 0) {
    snprintf(
        cmd, sizeof cmd,
        "gcc '%s/objs/libcore/widget.o' '%s/objs/app_v1/main.o' -o '%s'",
        tb_var_root(), tb_var_root(), bin);
  } else {
    snprintf(
        cmd, sizeof cmd,
        "gcc '%s/objs/libcore/widget.o' '%s/objs/app_v2/aux.o' -o '%s'",
        tb_var_root(), tb_var_root(), bin);
  }
  if (run_cmd(cmd) != 0) {
    return -1;
  }
  tb_ring_note(bin, gen);
  return 0;
}

static int build_target(const char *target, int pristine) {
  tb_compile_unit("libcore/widget.c", "objs/libcore/widget.o", pristine ? 1 : 0);
  if (strcmp(target, "app_v1") == 0) {
    tb_compile_unit("app_v1/main.c", "objs/app_v1/main.o", pristine ? 1 : 0);
    return tb_link_target("app_v1", "objs/app_v1/main.o", "bins/app_v1.bin");
  }
  tb_compile_unit("app_v2/aux.c", "objs/app_v2/aux.o", pristine ? 1 : 0);
  return tb_link_target("app_v2", "objs/app_v2/aux.o", "bins/app_v2.bin");
}

int tb_pristine_tree(void) {
  char cmd[384];
  snprintf(
      cmd, sizeof cmd,
      "find '%s/objs' '%s/bins' -mindepth 1 -delete 2>/dev/null; "
      "mkdir -p '%s/objs' '%s/bins'",
      tb_var_root(), tb_var_root(), tb_var_root(), tb_var_root());
  g_widget_dirty = 0;
  tb_compile_journal_set_mode("pristine");
  return run_cmd(cmd);
}

int tb_fast_rebuild_targets(const char **targets, int n_targets) {
  tb_compile_journal_set_mode("fast");
  for (int i = 0; i < n_targets; i++) {
    if (build_target(targets[i], 0) != 0) {
      return -1;
    }
  }
  return 0;
}

int tb_pristine_rebuild_targets(const char **targets, int n_targets) {
  tb_compile_journal_set_mode("pristine");
  tb_pristine_tree();
  for (int i = 0; i < n_targets; i++) {
    if (build_target(targets[i], 1) != 0) {
      return -1;
    }
  }
  return 0;
}
