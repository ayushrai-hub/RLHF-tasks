#include "trace_store.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int emit_trace_json(const char *out_path);
int run_apply_step(const char *profile, const char *principal, const char *state_path);
int run_reach_step(const char *state_path, const char *launch_tag, int inherit_flag);
int run_audit_step(const char *state_path);

int run_round(const char *profile, const char *principal, const char *launch_tag, int inherit_flag)
{
    const char *state = "/app/work/row_state.env";
    if (run_apply_step(profile, principal, state) != 0) {
        return -1;
    }
    if (run_reach_step(state, launch_tag, inherit_flag) != 0) {
        return -1;
    }
    return run_audit_step(state);
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        (void)fprintf(stderr, "usage: h7_drv round|clear|emit ...\n");
        return 2;
    }
    if (strcmp(argv[1], "round") == 0) {
        const char *profile = "w0_short";
        const char *principal = "direct";
        const char *launch_tag = "posix";
        int inherit_flag = 1;
        for (int i = 2; i < argc; i++) {
            if (strcmp(argv[i], "--profile") == 0 && i + 1 < argc) {
                profile = argv[++i];
            } else if (strcmp(argv[i], "--principal") == 0 && i + 1 < argc) {
                principal = argv[++i];
            } else if (strcmp(argv[i], "--launch") == 0 && i + 1 < argc) {
                launch_tag = argv[++i];
            } else if (strcmp(argv[i], "--inherit") == 0 && i + 1 < argc) {
                inherit_flag = atoi(argv[++i]);
            }
        }
        return run_round(profile, principal, launch_tag, inherit_flag) == 0 ? 0 : 1;
    }
    if (strcmp(argv[1], "clear") == 0) {
        trace_store_clear();
        return 0;
    }
    if (strcmp(argv[1], "emit") == 0) {
        const char *out = "/app/output/h7_trace.json";
        for (int i = 2; i < argc; i++) {
            if (strcmp(argv[i], "--out") == 0 && i + 1 < argc) {
                out = argv[++i];
            }
        }
        return emit_trace_json(out) == 0 ? 0 : 1;
    }
    return 2;
}
