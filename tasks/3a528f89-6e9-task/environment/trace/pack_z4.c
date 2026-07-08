#include <stdio.h>
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

int emit_z4(const void *rows, size_t n, const char *out_json, const char *chain_stamp)
{
    if (!rows || !out_json || !chain_stamp || n == 0) {
        return -1;
    }
    const trace_row *r = (const trace_row *)rows;
    FILE *fp = fopen(out_json, "w");
    if (!fp) {
        return -2;
    }
    fprintf(fp, "{\n  \"rows\": [\n");
    for (size_t i = 0; i < n; i++) {
        fprintf(
            fp,
            "    {\"profile\": \"%s\", \"main_digest_hex\": \"%s\", \"dep_digest_hex\": \"%s\", "
            "\"lineage_col\": \"%s\", \"so_delta\": %u, \"scan_violations\": %u, \"fault_obs\": %u}%s\n",
            r[i].profile,
            r[i].main_digest_hex,
            r[i].dep_digest_hex,
            r[i].lineage_col,
            r[i].so_delta,
            r[i].scan_violations,
            r[i].fault_obs,
            (i + 1 < n) ? "," : "");
    }
    fprintf(
        fp,
        "  ],\n  \"summary\": {\"row_count\": %zu, \"batch_stamp\": \"tag-v2\", \"chain_stamp\": \"%s\"}\n}\n",
        n,
        chain_stamp);
    fclose(fp);
    return 0;
}
