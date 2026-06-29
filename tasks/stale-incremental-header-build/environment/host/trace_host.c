#include "lib_iface.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int run_shell(const char *cmd) {
  return system(cmd) == 0 ? 0 : -1;
}

static void bin_path(const char *target, char *out, size_t cap) {
  snprintf(out, cap, "%s/bins/%s.bin", tb_var_root(), target);
}

static int digest_for_target(const char *target, char *hex, char *cap) {
  char bin[512];
  bin_path(target, bin, sizeof bin);
  memset(hex, 0, 65);
  memset(cap, 0, TB_TAG_LEN);
  if (tb_file_sha256_hex(bin, hex, 65) != 0) {
    return -1;
  }
  if (tb_read_cap_label(bin, cap, TB_TAG_LEN) != 0) {
    snprintf(cap, TB_TAG_LEN, "%s", "unknown");
  }
  return 0;
}

static int run_bld(const char *cap_value, int pristine) {
  char cmd[512];
  if (pristine) {
    snprintf(
        cmd, sizeof cmd, "/app/environment/bin/bld_host --pristine '%s'",
        cap_value);
  } else {
    snprintf(cmd, sizeof cmd, "/app/environment/bin/bld_host '%s'", cap_value);
  }
  return run_shell(cmd);
}

static void add_row(
    struct trace_ctx *tx, const char *plan, const char *target,
    const char *fast_hex, const char *pr_hex, const char *cap) {
  struct trace_row *r = &tx->rows[tx->n_rows++];
  snprintf(r->plan_id, sizeof r->plan_id, "%s", plan);
  snprintf(r->target, sizeof r->target, "%s", target);
  snprintf(r->fast_hex, sizeof r->fast_hex, "%s", fast_hex);
  snprintf(r->pristine_hex, sizeof r->pristine_hex, "%s", pr_hex);
  snprintf(r->cap_label, sizeof r->cap_label, "%s", cap);
}

static int measure_plan(
    struct trace_ctx *tx, const char *plan_id, const char *cap_value,
    const char **targets, int n_targets, int same_sec) {
  if (run_bld("cap_r1", 1) != 0) {
    return -1;
  }
  if (run_bld(cap_value, 0) != 0) {
    return -1;
  }
  if (same_sec) {
    char cmd[512];
    snprintf(
        cmd, sizeof cmd, "/app/environment/scripts/touch_same_sec.sh '%s'",
        tb_env_root());
    if (run_shell(cmd) != 0) {
      return -1;
    }
    if (run_bld(cap_value, 0) != 0) {
      return -1;
    }
  }
  for (int i = 0; i < n_targets; i++) {
    char fast_hex[65];
    char pr_hex[65];
    char cap_fast[TB_TAG_LEN];
    digest_for_target(targets[i], fast_hex, cap_fast);
    if (run_bld(cap_value, 1) != 0) {
      return -1;
    }
    char cap_pr[TB_TAG_LEN];
    digest_for_target(targets[i], pr_hex, cap_pr);
    (void)cap_pr;
    add_row(tx, plan_id, targets[i], fast_hex, pr_hex, cap_fast);
  }
  return 0;
}

static int measure_cap_rollback(
    struct trace_ctx *tx, const char *plan_id, const char *mid_cap,
    const char *final_cap, const char **targets, int n_targets) {
  if (run_bld("cap_r1", 1) != 0) {
    return -1;
  }
  if (run_bld(mid_cap, 0) != 0) {
    return -1;
  }
  if (run_bld(final_cap, 0) != 0) {
    return -1;
  }
  for (int i = 0; i < n_targets; i++) {
    char fast_hex[65];
    char pr_hex[65];
    char cap_fast[TB_TAG_LEN];
    digest_for_target(targets[i], fast_hex, cap_fast);
    if (run_bld(final_cap, 1) != 0) {
      return -1;
    }
    char cap_pr[TB_TAG_LEN];
    digest_for_target(targets[i], pr_hex, cap_pr);
    (void)cap_pr;
    add_row(tx, plan_id, targets[i], fast_hex, pr_hex, cap_fast);
  }
  return 0;
}

int main(int argc, char **argv) {
  tb_paths_init("/app/environment");
  (void)argc;
  (void)argv;
  mkdir("/app/output", 0755);
  struct trace_row rows[32];
  struct trace_ctx tx = {rows, 0, 32};
  const char *both[] = {"app_v1", "app_v2"};
  if (measure_plan(&tx, "header_bump", "cap_r2", both, 2, 0) != 0) {
    return 1;
  }
  if (run_bld("cap_r2", 1) != 0) {
    return 1;
  }
  if (run_bld("cap_r2", 0) != 0) {
    return 1;
  }
  {
    char fast_hex[65];
    char pr_hex[65];
    char cap_fast[TB_TAG_LEN];
    digest_for_target("app_v1", fast_hex, cap_fast);
    if (run_bld("cap_r2", 1) != 0) {
      return 1;
    }
    digest_for_target("app_v1", pr_hex, cap_fast);
    add_row(&tx, "unchanged_control", "app_v1", fast_hex, pr_hex, cap_fast);
  }
  if (measure_cap_rollback(&tx, "cap_rollback", "cap_r3", "cap_r2", both, 2) != 0) {
    return 1;
  }
  if (measure_plan(&tx, "same_second_seq", "cap_r3", both, 2, 1) != 0) {
    return 1;
  }
  return sink_d(&tx, tb_out_trace());
}
