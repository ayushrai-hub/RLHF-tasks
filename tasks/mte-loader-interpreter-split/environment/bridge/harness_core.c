#include "dig01.h"

#include "../trace/chain_io.h"
#include "../trace/persist_v5.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char profile[16];
    char main_digest_hex[17];
    char dep_digest_hex[17];
    char lineage_col[17];
    unsigned so_delta;
    unsigned scan_violations;
    unsigned fault_obs;
} trace_row;

int stage_load_merge(const uint8_t *note, size_t nlen, const char *path_token, uint32_t *out_flags);
int scan_face_run(const char *main_elf, char **so_list, size_t nso, uint32_t *violations);
int stage_link_emit(const char *spec_path, uint8_t flags, char *out_path, size_t olen);
int emit_face_write(const void *rows, size_t n, const char *out_json, const char *chain_stamp);
int main_only_audit(const char *main_elf, uint32_t *violations);

static const char *MAIN_ELF = "/app/environment/fixtures/main_a64.elf";
static const char *DEP_TAGGED = "/app/environment/fixtures/dep_tagged.so";
static const char *DEP_UNTAGGED = "/app/environment/fixtures/dep_untagged.so";
static const char *INTERP = "/lib/ld-linux-aarch64.so.1";
static const char *OUT_JSON = "/app/output/tag_reconcile.json";
static const char *CHAIN_PATH = "/app/work/tag_chain.tsv";
static const char *PERSIST_PATH = "/app/work/tag_persist.bin";
static const char *ROUTES_PATH = "/app/environment/cfg/profile_routes.toml";

static unsigned read_obs(const char *profile)
{
    char path[128];
    snprintf(path, sizeof(path), "/app/environment/fixtures/buf_samples/%s.log", profile);
    FILE *fp = fopen(path, "r");
    if (!fp) {
        return 0;
    }
    char line[128];
    unsigned obs = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (sscanf(line, "obs=%u", &obs) == 1) {
            break;
        }
    }
    fclose(fp);
    return obs;
}

static int route_spec(const char *profile, char *out, size_t olen)
{
    FILE *fp = fopen(ROUTES_PATH, "r");
    if (!fp) {
        return -1;
    }
    char line[128];
    int active = 0;
    char want[32];
    snprintf(want, sizeof(want), "[%s]", profile);
    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, want)) {
            active = 1;
            continue;
        }
        if (active && line[0] == '[') {
            break;
        }
        if (active && strstr(line, "spec")) {
            char slot[64];
            if (sscanf(line, " spec = \"%63[^\"]\"", slot) == 1) {
                snprintf(out, olen, "/app/environment/fixtures/spec_t2/%s", slot);
                fclose(fp);
                return 0;
            }
        }
    }
    fclose(fp);
    return -2;
}

static int route_dep_path(const char *profile, char *out, size_t olen)
{
    FILE *fp = fopen(ROUTES_PATH, "r");
    if (!fp) {
        return -1;
    }
    char line[128];
    int active = 0;
    char want[32];
    snprintf(want, sizeof(want), "[%s]", profile);
    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, want)) {
            active = 1;
            continue;
        }
        if (active && line[0] == '[') {
            break;
        }
        if (active && strstr(line, "dep_fixture")) {
            char slot[64];
            if (sscanf(line, " dep_fixture = \"%63[^\"]\"", slot) == 1) {
                snprintf(out, olen, "/app/environment/fixtures/%s", slot);
                fclose(fp);
                return 0;
            }
        }
    }
    fclose(fp);
    return -2;
}

static void lineage_from_merge(const char *path_token, uint32_t flags, char *out, size_t olen)
{
    uint64_t h = dig01_fnv1a64((const uint8_t *)path_token, strlen(path_token));
    uint8_t buf[32];
    size_t n = 0;
    char prefix[32];
    snprintf(prefix, sizeof(prefix), "%016llx", (unsigned long long)(h & 0xffffffffffffULL));
    memcpy(buf, prefix, 16);
    n = 16;
    memcpy(buf + n, &flags, sizeof(flags));
    n += sizeof(flags);
    uint64_t d = dig01_fnv1a64(buf, n);
    snprintf(out, olen, "%016llx", (unsigned long long)(d & 0xffffffffffffULL));
}

static unsigned count_delta(const char *main_hex, char **sos, size_t nso)
{
    unsigned delta = 0;
    for (size_t i = 0; i < nso; i++) {
        char dep_hex[32];
        if (dig01_digest_hex(sos[i], dep_hex, sizeof(dep_hex)) != 0) {
            continue;
        }
        if (strcmp(main_hex, dep_hex) != 0) {
            delta++;
        }
    }
    return delta;
}

static int link_asymmetry(void)
{
    char out_a[128];
    char out_b[128];
    if (stage_link_emit("/app/environment/fixtures/spec_t2/build_a.toml", 1, out_a, sizeof(out_a)) != 0) {
        return 3;
    }
    if (stage_link_emit("/app/environment/fixtures/spec_t2/build_b.toml", 1, out_b, sizeof(out_b)) != 0) {
        return 3;
    }
    const char *ta = strrchr(out_a, 'g');
    const char *tb = strrchr(out_b, 'g');
    if (!ta || !tb) {
        return 3;
    }
    return (ta[1] == tb[1]) ? 0 : 3;
}

static unsigned adjusted_fault(unsigned base, unsigned violations)
{
    int v = (int)base - (int)violations;
    return v < 0 ? 0 : (unsigned)v;
}

static int journal_line(
    const char *profile,
    unsigned violations,
    int asym,
    unsigned fault_obs,
    const char *lineage)
{
    return chain_append(CHAIN_PATH, profile, violations, asym, fault_obs, lineage);
}

int harness_run_batch(void)
{
    char *sos[2] = { (char *)DEP_TAGGED, (char *)DEP_UNTAGGED };
    trace_row rows[2];
    const char *profiles[2] = { "fw_b", "fw_a" };
    char main_hex[32];
    if (dig01_digest_hex(MAIN_ELF, main_hex, sizeof(main_hex)) != 0) {
        return 1;
    }
    uint8_t note[32];
    size_t nlen = 0;
    if (dig01_note_bytes(MAIN_ELF, note, &nlen) != 0) {
        return 2;
    }
    uint32_t flags = 0;
    if (stage_load_merge(note, nlen, INTERP, &flags) != 0) {
        return 3;
    }
    if (persist_reset(PERSIST_PATH) != 0) {
        return 4;
    }
    uint32_t decoy_viol = 0;
    if (main_only_audit(MAIN_ELF, &decoy_viol) != 0) {
        return 5;
    }
    if (persist_seal_decoy(PERSIST_PATH, decoy_viol) != 0) {
        return 6;
    }
    uint32_t violations = 0;
    if (scan_face_run(MAIN_ELF, sos, 2, &violations) != 0) {
        return 7;
    }
    unsigned delta = count_delta(main_hex, sos, 2);
    int asym = link_asymmetry();
    if (persist_seal_walk(PERSIST_PATH, violations, asym) != 0) {
        return 8;
    }
    char lineage[32];
    lineage_from_merge(INTERP, flags, lineage, sizeof(lineage));
    unsigned base_a = read_obs("fw_a");
    unsigned shared_fault = adjusted_fault(base_a, violations);
    if (chain_reset(CHAIN_PATH) != 0) {
        return 9;
    }
    for (int i = 0; i < 2; i++) {
        char dep_path[128];
        if (route_dep_path(profiles[i], dep_path, sizeof(dep_path)) != 0) {
            strncpy(dep_path, DEP_UNTAGGED, sizeof(dep_path) - 1);
        }
        char dep_hex[32];
        if (dig01_digest_hex(dep_path, dep_hex, sizeof(dep_hex)) != 0) {
            return 10;
        }
        uint32_t row_viol = violations;
        if (persist_viol_for_profile(PERSIST_PATH, profiles[i], &row_viol) != 0) {
            return 11;
        }
        memset(&rows[i], 0, sizeof(rows[i]));
        strncpy(rows[i].profile, profiles[i], sizeof(rows[i].profile) - 1);
        strncpy(rows[i].main_digest_hex, main_hex, sizeof(rows[i].main_digest_hex) - 1);
        strncpy(rows[i].dep_digest_hex, dep_hex, sizeof(rows[i].dep_digest_hex) - 1);
        strncpy(rows[i].lineage_col, lineage, sizeof(rows[i].lineage_col) - 1);
        rows[i].so_delta = delta;
        rows[i].scan_violations = row_viol;
        if (strcmp(profiles[i], "fw_b") == 0 && asym > 0) {
            rows[i].fault_obs = read_obs("fw_b");
        } else if (strcmp(profiles[i], "fw_b") == 0) {
            rows[i].fault_obs = shared_fault;
        } else {
            rows[i].fault_obs = shared_fault;
        }
        if (journal_line(profiles[i], row_viol, asym, rows[i].fault_obs, lineage) != 0) {
            return 12;
        }
    }
    char chain_stamp[32];
    if (chain_stamp_hex(CHAIN_PATH, chain_stamp, sizeof(chain_stamp)) != 0) {
        return 13;
    }
    trace_row ordered[2];
    ordered[0] = rows[1];
    ordered[1] = rows[0];
    return emit_face_write(ordered, 2, OUT_JSON, chain_stamp);
}

int main(void)
{
    return harness_run_batch() == 0 ? 0 : 1;
}
