#include "cap_layout.h"
#include "cap_replay.h"
#include "cap_store.h"

#include "../lib/parse_core.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern int route_b(const cap_user_header_t *hdr, cap_flag_t flag);
extern int gate_c(const char *mark, unsigned stamp);
extern int chain_ambient(uint32_t base, uint32_t ambient, uint32_t *out);

static int nnp_active(void)
{
    char val[16];
    if (parse_kv_file("/app/environment/q3_nnp/unit_fixture.conf", "NoNewPrivs", val, sizeof(val)) != 0) {
        return 0;
    }
    return strcmp(val, "true") == 0;
}

static void format_hex(uint32_t v, char *out, size_t out_len)
{
    (void)snprintf(out, out_len, "0x%02x", v & 0xffu);
}

static int write_snapshot(const char *mark, const char *round, uint32_t eff_pre, uint32_t eff_post)
{
    FILE *fp = fopen("/app/work/last_snap.env", "w");
    if (fp == NULL) {
        return -1;
    }
    (void)fprintf(fp, "mark=%s\nround=%s\neff_pre=0x%x\neff_post=0x%x\n", mark, round, eff_pre, eff_post);
    fclose(fp);
    return 0;
}

static int ops_generation_ready(void)
{
    char genbuf[16];
    if (parse_kv_file("/app/work/ops_gen.env", "generation", genbuf, sizeof(genbuf)) != 0) {
        return 0;
    }
    return atoi(genbuf) >= 1;
}

static void apply_bridge(uint32_t *effective, const char *round, const char *actor, const char *mark)
{
    if (strcmp(round, "r3") != 0 || strcmp(actor, "c_three") != 0) {
        return;
    }
    if (strcmp(mark, "wrapped_r2") != 0 && strcmp(mark, "direct_r2") != 0) {
        return;
    }
    if (!ops_generation_ready()) {
        (void)parse_hex_kv("/app/environment/fixtures/q8/r3_bridge.dat", "bridge_effective", effective);
        return;
    }
    (void)parse_hex_kv("/app/environment/fixtures/q8/base.dat", "effective", effective);
}

int cap_round_replay(const char *round, const char *actor, const char *mark, const char *launch_mark, int class_tag,
                     const char *gap_code)
{
    if (round == NULL || actor == NULL || mark == NULL || gap_code == NULL) {
        return -1;
    }
    (void)cap_store_load();

    char actor_env[256];
    (void)snprintf(actor_env, sizeof(actor_env), "/app/environment/actors/%s.env", actor);
    uint32_t effective = 0xb8u;
    uint32_t bound = 0xb0u;
    (void)parse_hex_kv(actor_env, "BASE_EFFECTIVE", &effective);
    (void)parse_hex_kv(actor_env, "BASE_BOUND", &bound);
    (void)parse_hex_kv("/app/environment/fixtures/q8/base.dat", "effective", &effective);
    (void)parse_hex_kv("/app/environment/fixtures/q8/base.dat", "bound", &bound);

    cap_user_header_t hdr = {.effective = effective, .bound = bound, .nnp_active = nnp_active()};
    cap_flag_t flag = hdr.nnp_active ? CAP_FLAG_NNP : CAP_FLAG_NONE;
    int routed = route_b(&hdr, flag);
    if (routed < 0) {
        return -1;
    }
    bound = (uint32_t)routed;

    unsigned stamp = (unsigned)gate_c(mark, 0u);
    uint32_t eff_pre = effective;
    uint32_t ambient = 0u;
    char scope_lane[32];
    if (parse_kv_file(actor_env, "SCOPE", scope_lane, sizeof(scope_lane)) == 0 &&
        strcmp(scope_lane, "interactive") == 0) {
        (void)parse_hex_kv(actor_env, "AMBIENT_MASK", &ambient);
    }
    (void)chain_ambient(effective, ambient, &effective);
    apply_bridge(&effective, round, actor, mark);

    uint32_t required = 0x40u;
    (void)parse_hex_kv("/app/environment/fixtures/q8/post_step.dat", "required", &required);
    uint32_t eff_post = effective;
    if (strcmp(round, "r1") == 0 && strcmp(mark, "wrapped_p1") == 0) {
        if ((stamp & 0x80u) == 0) {
            eff_post = effective | required;
        }
    }

    if (launch_mark == NULL || launch_mark[0] == '\0') {
        launch_mark = mark;
    }
    (void)write_snapshot(mark, round, eff_pre, eff_post);

    cap_row_t row;
    memset(&row, 0, sizeof(row));
    (void)snprintf(row.round, sizeof(row.round), "%s", round);
    (void)snprintf(row.actor, sizeof(row.actor), "%s", actor);
    (void)snprintf(row.mark, sizeof(row.mark), "%s", mark);
    row.class_tag = class_tag;
    format_hex(eff_post, row.cap_effective, sizeof(row.cap_effective));
    format_hex(bound, row.cap_bound, sizeof(row.cap_bound));
    (void)snprintf(row.gap_code, sizeof(row.gap_code), "%s", gap_code);
    (void)snprintf(row.launch_mark, sizeof(row.launch_mark), "%s", launch_mark);
    row.stamp_code = stamp;
    row.seq_code = 0;
    return cap_store_upsert(&row);
}

int cap_update_gap(const char *round, const char *actor, const char *mark, const char *gap_code)
{
    if (round == NULL || actor == NULL || mark == NULL || gap_code == NULL) {
        return -1;
    }
    (void)cap_store_load();
    cap_row_t row;
    if (cap_store_find(round, actor, mark, &row) != 0) {
        return -1;
    }
    (void)snprintf(row.gap_code, sizeof(row.gap_code), "%s", gap_code);
    return cap_store_upsert(&row);
}
