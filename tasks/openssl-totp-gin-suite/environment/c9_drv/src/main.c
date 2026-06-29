#include "k9.h"

#include <stdio.h>
#include <string.h>

static void usage(const char *prog) {
    fprintf(stderr, "usage: %s enroll --handle H --store-dir D [--base-url U]\n", prog);
    fprintf(stderr, "       %s mfa --account-id A --store-dir D [--base-url U] [--clock-epoch E]\n", prog);
    fprintf(stderr, "       %s verify --account-id A --token T --store-dir D [--clock-epoch E]\n", prog);
    fprintf(stderr, "       %s probe --account-id A --store-dir D [--clock-epoch E]\n", prog);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        usage(argv[0]);
        return 2;
    }
    const char *cmd = argv[1];
    char *cmd_argv[32];
    int cmd_argc = 0;
    for (int i = 2; i < argc && cmd_argc < 32; i++) {
        cmd_argv[cmd_argc++] = argv[i];
    }

    if (strcmp(cmd, "enroll") == 0) {
        int rc = run_enroll_cmd(cmd_argc, cmd_argv);
        if (rc == 2) {
            usage(argv[0]);
        }
        return rc;
    }
    if (strcmp(cmd, "mfa") == 0) {
        int rc = run_mfa_cmd(cmd_argc, cmd_argv);
        if (rc == 2) {
            usage(argv[0]);
        }
        return rc;
    }
    if (strcmp(cmd, "verify") == 0) {
        int rc = run_verify_cmd(cmd_argc, cmd_argv);
        if (rc == 2) {
            usage(argv[0]);
        }
        return rc;
    }
    if (strcmp(cmd, "probe") == 0) {
        int rc = run_probe_cmd(cmd_argc, cmd_argv);
        if (rc == 2) {
            usage(argv[0]);
        }
        return rc;
    }

    usage(argv[0]);
    return 2;
}
