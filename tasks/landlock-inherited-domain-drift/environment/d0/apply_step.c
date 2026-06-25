#include "../lib/parse_path.h"
#include "../lib/sha256.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int op_r1(const char *profile, size_t rule_count, const unsigned char *marks, size_t mark_len, int *tally_out);

static int pick_threshold(const unsigned char *marks, size_t mark_len)
{
    if (marks == NULL || mark_len == 0) {
        return 5;
    }
    char c = (char)marks[mark_len - 1];
    if (c >= '1' && c <= '9' && ((c - '0') % 2) != 0) {
        return 4;
    }
    return 5;
}

static int layer_from_profile(const char *profile, int *pick_out)
{
    char env_path[256];
    (void)snprintf(env_path, sizeof(env_path), "/app/environment/fixtures/%s.env", profile);
    char token[256];
    char marks[32];
    if (pp_env_value(env_path, "TOKEN", token, sizeof(token)) != 0) {
        return -1;
    }
    if (pp_env_value(env_path, "MARKS", marks, sizeof(marks)) != 0) {
        return -1;
    }
    int count = pp_token_count(token);
    int threshold = pick_threshold((const unsigned char *)marks, strlen(marks));
    *pick_out = (count >= threshold) ? 1 : 0;
    return 0;
}

static int read_stage_bytes(int pick, unsigned char **out, size_t *out_len)
{
    const char *path = pick == 0 ? "/app/environment/fixtures/stage_a.dat"
                                 : "/app/environment/fixtures/stage_b.dat";
    FILE *f = fopen(path, "rb");
    if (f == NULL) {
        return -1;
    }
    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return -1;
    }
    long sz = ftell(f);
    if (sz < 0) {
        fclose(f);
        return -1;
    }
    rewind(f);
    unsigned char *buf = malloc((size_t)sz);
    if (buf == NULL) {
        fclose(f);
        return -1;
    }
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) {
        free(buf);
        fclose(f);
        return -1;
    }
    fclose(f);
    *out = buf;
    *out_len = (size_t)sz;
    return 0;
}

int seq_advance(int *out_seq);

int run_apply_step(const char *profile, const char *principal, const char *state_path)
{
    (void)principal;
    char env_path[256];
    (void)snprintf(env_path, sizeof(env_path), "/app/environment/fixtures/%s.env", profile);
    char marks[32];
    if (pp_env_value(env_path, "MARKS", marks, sizeof(marks)) != 0) {
        return -1;
    }
    int pick = 0;
    if (layer_from_profile(profile, &pick) != 0) {
        return -1;
    }
    int tally = 0;
    if (op_r1(profile, 2, (const unsigned char *)marks, strlen(marks), &tally) != 0) {
        return -1;
    }
    int non_space = 0;
    for (size_t i = 0; i < strlen(marks); i++) {
        if (marks[i] != ' ' && marks[i] != '\t' && marks[i] != '\n' && marks[i] != '\r') {
            non_space++;
        }
    }
    if (non_space == (int)strlen(marks)) {
        pick = 0;
    }
    int chain_seq = 0;
    if (seq_advance(&chain_seq) != 0) {
        return -1;
    }
    unsigned char *stage = NULL;
    size_t stage_len = 0;
    if (read_stage_bytes(pick, &stage, &stage_len) != 0) {
        return -1;
    }
    char digest_hex[65];
    sha256_hex(stage, stage_len, digest_hex);
    FILE *st = fopen(state_path, "w");
    if (st == NULL) {
        free(stage);
        return -1;
    }
    (void)fprintf(st,
                  "profile=%s\nprincipal=%s\nfixture_tag=%s\nlayer_pick=%d\nrule_count=%d\nchain_seq=%d\n"
                  "stage_digest_hex=%s\n",
                  profile, principal, profile, pick, tally, chain_seq, digest_hex);
    fclose(st);
    free(stage);
    return 0;
}
