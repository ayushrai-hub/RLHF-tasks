#include "../lib/parse_path.h"
#include "../lib/sha256.h"
#include "trace_store.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int probe_r5(const char *principal, int probe_code, const char *target_root, char *row_out, size_t row_cap);

static int load_state_field(const char *path, const char *key, char *out, size_t cap)
{
    FILE *f = fopen(path, "r");
    if (f == NULL) {
        return -1;
    }
    char line[512];
    size_t klen = strlen(key);
    while (fgets(line, sizeof(line), f) != NULL) {
        if (strncmp(line, key, klen) == 0 && line[klen] == '=') {
            size_t n = strcspn(line + klen + 1, "\r\n");
            if (n >= cap) {
                fclose(f);
                return -1;
            }
            memcpy(out, line + klen + 1, n);
            out[n] = '\0';
            fclose(f);
            return 0;
        }
    }
    fclose(f);
    return -1;
}

static void snap_mark(const char *seed_path, const char *admission, char *out, size_t cap)
{
    FILE *f = fopen(seed_path, "r");
    char seed[128] = "";
    if (f != NULL) {
        if (fgets(seed, sizeof(seed), f) != NULL) {
            size_t n = strcspn(seed, "\r\n");
            seed[n] = '\0';
        }
        fclose(f);
    }
    char payload[256];
    (void)snprintf(payload, sizeof(payload), "%s%s", seed, admission);
    sha256_hex_prefix((const unsigned char *)payload, strlen(payload), 8, out);
    (void)cap;
}

static int expected_reach(const char *profile, int pick, char *out, size_t cap)
{
    char env_path[256];
    (void)snprintf(env_path, sizeof(env_path), "/app/environment/fixtures/%s.env", profile);
    char envelope[256];
    if (pp_env_value(env_path, "ENVELOPE", envelope, sizeof(envelope)) != 0) {
        return -1;
    }
    const char *stage_path = pick == 0 ? "/app/environment/fixtures/stage_a.dat"
                                       : "/app/environment/fixtures/stage_b.dat";
    FILE *sf = fopen(stage_path, "rb");
    if (sf == NULL) {
        return -1;
    }
    fseek(sf, 0, SEEK_END);
    long sz = ftell(sf);
    rewind(sf);
    unsigned char *stage = malloc((size_t)sz);
    if (stage == NULL) {
        fclose(sf);
        return -1;
    }
    fread(stage, 1, (size_t)sz, sf);
    fclose(sf);
    unsigned char payload[512];
    size_t elen = strlen(envelope);
    if (elen + (size_t)sz >= sizeof(payload)) {
        free(stage);
        return -1;
    }
    memcpy(payload, envelope, elen);
    memcpy(payload + elen, stage, (size_t)sz);
    sha256_hex_prefix(payload, elen + (size_t)sz, 16, out);
    free(stage);
    (void)cap;
    return 0;
}

static int rolling_self_check(const char *reach, const char *handoff, int rule_count, char *out, size_t cap)
{
    char payload[128];
    (void)snprintf(payload, sizeof(payload), "%s%s%d", reach, handoff, rule_count);
    sha256_hex_prefix((const unsigned char *)payload, strlen(payload), 16, out);
    (void)cap;
    return 0;
}

static void maybe_write_profile_carry(const char *profile, const char *principal,
                                      const char *stage_digest_hex)
{
    if (profile == NULL || principal == NULL || stage_digest_hex == NULL) {
        return;
    }
    if (strcmp(profile, "w0_short") != 0 || strcmp(principal, "direct") != 0) {
        return;
    }
    FILE *out = fopen("/app/work/profile_carry.txt", "w");
    if (out == NULL) {
        return;
    }
    char prefix[9];
    memcpy(prefix, stage_digest_hex, 8);
    prefix[8] = '\0';
    (void)fprintf(out, "%s\n", prefix);
    fclose(out);
}

int run_audit_step(const char *state_path)
{
    char profile[32];
    char principal[16];
    char fixture_tag[32];
    char digest_hex[65];
    char reach[17];
    char handoff[16];
    char pick_buf[16];
    char rules_buf[16];
    char chain_buf[16];
    if (load_state_field(state_path, "profile", profile, sizeof(profile)) != 0) {
        return -1;
    }
    if (load_state_field(state_path, "principal", principal, sizeof(principal)) != 0) {
        return -1;
    }
    if (load_state_field(state_path, "fixture_tag", fixture_tag, sizeof(fixture_tag)) != 0) {
        return -1;
    }
    if (load_state_field(state_path, "stage_digest_hex", digest_hex, sizeof(digest_hex)) != 0) {
        return -1;
    }
    if (load_state_field(state_path, "reach_digest", reach, sizeof(reach)) != 0) {
        return -1;
    }
    if (load_state_field(state_path, "handoff_label", handoff, sizeof(handoff)) != 0) {
        return -1;
    }
    if (load_state_field(state_path, "layer_pick", pick_buf, sizeof(pick_buf)) != 0) {
        return -1;
    }
    if (load_state_field(state_path, "rule_count", rules_buf, sizeof(rules_buf)) != 0) {
        return -1;
    }
    if (load_state_field(state_path, "chain_seq", chain_buf, sizeof(chain_buf)) != 0) {
        return -1;
    }
    int svc_flag = strcmp(principal, "svc") == 0 ? 1 : 0;
    char admit[8];
    if (probe_r5(principal, svc_flag, "/app/vault/primary", admit, sizeof(admit)) != 0) {
        return -1;
    }
    int rules = atoi(rules_buf);
    char self_check[17];
    if (rolling_self_check(reach, handoff, rules, self_check, sizeof(self_check)) != 0) {
        return -1;
    }
    char snap_a[9];
    char snap_b[9];
    char expect_reach[17];
    char b_admit[8];
    int pick = atoi(pick_buf);
    snap_mark("/app/environment/fixtures/snap_a_seed.txt", admit, snap_a, sizeof(snap_a));
    if (expected_reach(profile, pick, expect_reach, sizeof(expect_reach)) == 0 &&
        strcmp(expect_reach, reach) == 0) {
        (void)snprintf(b_admit, sizeof(b_admit), "%s", admit);
    } else if (strcmp(principal, "svc") == 0) {
        (void)snprintf(b_admit, sizeof(b_admit), "hold");
    } else {
        (void)snprintf(b_admit, sizeof(b_admit), "open");
    }
    snap_mark("/app/environment/fixtures/snap_b_seed.txt", b_admit, snap_b, sizeof(snap_b));
    trace_row_t row;
    memset(&row, 0, sizeof(row));
    (void)snprintf(row.profile, sizeof(row.profile), "%s", profile);
    (void)snprintf(row.principal, sizeof(row.principal), "%s", principal);
    (void)snprintf(row.fixture_tag, sizeof(row.fixture_tag), "%s", fixture_tag);
    (void)snprintf(row.stage_digest_hex, sizeof(row.stage_digest_hex), "%s", digest_hex);
    (void)snprintf(row.reach_digest, sizeof(row.reach_digest), "%s", reach);
    (void)snprintf(row.self_check_field, sizeof(row.self_check_field), "%s", self_check);
    (void)snprintf(row.admit_code, sizeof(row.admit_code), "%s", admit);
    (void)snprintf(row.snap_a_mark, sizeof(row.snap_a_mark), "%s", snap_a);
    (void)snprintf(row.snap_b_mark, sizeof(row.snap_b_mark), "%s", snap_b);
    (void)snprintf(row.handoff_label, sizeof(row.handoff_label), "%s", handoff);
    row.layer_pick = pick;
    row.rule_count = rules;
    row.chain_seq = atoi(chain_buf);
    maybe_write_profile_carry(profile, principal, digest_hex);
    return trace_store_add(&row);
}
