#include "cap_emit.h"
#include "cap_replay.h"
#include "cap_store.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc < 2) {
        (void)fprintf(stderr, "usage: cap_drv replay|emit|set-gap ...\n");
        return 2;
    }
    if (strcmp(argv[1], "replay") == 0) {
        const char *round = "r0";
        const char *actor = "a_one";
        const char *mark = "wrap_r0";
        const char *launch = "";
        int class_tag = 2;
        const char *gap = "G0";
        for (int i = 2; i < argc; i++) {
            if (strcmp(argv[i], "--round") == 0 && i + 1 < argc) {
                round = argv[++i];
            } else if (strcmp(argv[i], "--actor") == 0 && i + 1 < argc) {
                actor = argv[++i];
            } else if (strcmp(argv[i], "--mark") == 0 && i + 1 < argc) {
                mark = argv[++i];
            } else if (strcmp(argv[i], "--launch") == 0 && i + 1 < argc) {
                launch = argv[++i];
            } else if (strcmp(argv[i], "--class-tag") == 0 && i + 1 < argc) {
                class_tag = atoi(argv[++i]);
            } else if (strcmp(argv[i], "--gap") == 0 && i + 1 < argc) {
                gap = argv[++i];
            }
        }
        return cap_round_replay(round, actor, mark, launch, class_tag, gap) == 0 ? 0 : 1;
    }
    if (strcmp(argv[1], "set-gap") == 0) {
        const char *round = "";
        const char *actor = "";
        const char *mark = "";
        const char *gap = "G0";
        for (int i = 2; i < argc; i++) {
            if (strcmp(argv[i], "--round") == 0 && i + 1 < argc) {
                round = argv[++i];
            } else if (strcmp(argv[i], "--actor") == 0 && i + 1 < argc) {
                actor = argv[++i];
            } else if (strcmp(argv[i], "--mark") == 0 && i + 1 < argc) {
                mark = argv[++i];
            } else if (strcmp(argv[i], "--gap") == 0 && i + 1 < argc) {
                gap = argv[++i];
            }
        }
        return cap_update_gap(round, actor, mark, gap) == 0 ? 0 : 1;
    }
    if (strcmp(argv[1], "emit") == 0) {
        const char *out = "/app/output/cap_audit.json";
        for (int i = 2; i < argc; i++) {
            if (strcmp(argv[i], "--out") == 0 && i + 1 < argc) {
                out = argv[++i];
            }
        }
        (void)cap_store_load();
        return emit_cap_json(out) == 0 ? 0 : 1;
    }
    return 2;
}
