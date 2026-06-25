#include "../lib/parse_path.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int gate_r3(const char *launch_tag, int inherit_flag, const char *domain_blob, size_t blob_len,
            char *handoff_out, size_t handoff_cap);
int gate_r3_reach(const unsigned char *envelope, size_t env_len, const unsigned char *stage,
                  size_t stage_len, char *reach_out, size_t reach_cap);

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

int run_reach_step(const char *state_path, const char *launch_tag, int inherit_flag)
{
    char profile[32];
    char pick_buf[16];
    if (load_state_field(state_path, "profile", profile, sizeof(profile)) != 0) {
        return -1;
    }
    if (load_state_field(state_path, "layer_pick", pick_buf, sizeof(pick_buf)) != 0) {
        return -1;
    }
    int pick = atoi(pick_buf);
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
    size_t env_len = strlen(envelope);
    size_t payload_len = env_len + (size_t)sz;
    unsigned char *reach_payload = malloc(payload_len + 32);
    if (reach_payload == NULL) {
        free(stage);
        return -1;
    }
    memcpy(reach_payload, envelope, env_len);
    memcpy(reach_payload + env_len, stage, (size_t)sz);
    if (strcmp(profile, "w0_long") == 0) {
        FILE *carry_f = fopen("/app/work/profile_carry.txt", "r");
        if (carry_f != NULL) {
            char carry[16] = "";
            if (fgets(carry, sizeof(carry), carry_f) != NULL) {
                size_t clen = strcspn(carry, "\r\n");
                carry[clen] = '\0';
                if (clen > 0 && payload_len + clen <= payload_len + 16) {
                    memcpy(reach_payload + payload_len, carry, clen);
                    payload_len += clen;
                }
            }
            fclose(carry_f);
        }
    }
    char reach[17];
    if (gate_r3_reach(reach_payload, env_len, stage, (size_t)sz, reach, sizeof(reach)) != 0) {
        free(reach_payload);
        free(stage);
        return -1;
    }
    free(reach_payload);
    char handoff[16];
    if (gate_r3(launch_tag, inherit_flag, envelope, strlen(envelope), handoff, sizeof(handoff)) != 0) {
        free(stage);
        return -1;
    }
    free(stage);
    FILE *st = fopen(state_path, "a");
    if (st == NULL) {
        return -1;
    }
    (void)fprintf(st, "reach_digest=%s\nhandoff_label=%s\n", reach, handoff);
    fclose(st);
    return 0;
}
