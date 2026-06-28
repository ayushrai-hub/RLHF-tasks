#include "lib_iface.h"

#include <stdio.h>
#include <string.h>

static char g_env[256];
static char g_var[256];
static char g_gen[256];
static char g_plan[256];
static char g_trace[256];

void tb_paths_init(const char *env_root) {
  snprintf(g_env, sizeof g_env, "%s", env_root);
  snprintf(g_var, sizeof g_var, "%s/var", env_root);
  snprintf(g_gen, sizeof g_gen, "%s/var/gen/version_slot.h", env_root);
  snprintf(g_plan, sizeof g_plan, "%s/data/run_plan.json", env_root);
  snprintf(g_trace, sizeof g_trace, "/app/output/rebuild_trace.json");
}

const char *tb_env_root(void) { return g_env; }
const char *tb_var_root(void) { return g_var; }
const char *tb_gen_hdr(void) { return g_gen; }
const char *tb_plan_path(void) { return g_plan; }
const char *tb_out_trace(void) { return g_trace; }
