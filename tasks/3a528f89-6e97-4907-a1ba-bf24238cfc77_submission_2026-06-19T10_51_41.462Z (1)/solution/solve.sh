#!/usr/bin/env bash
set -euo pipefail

cat > /app/environment/q2_auth/commit.sh <<'EOF'
#!/bin/bash
# ENV_ROOT defaults to /app/environment when unset.
bind_a() {
  local mark="${1:-}"
  local actor="${2:-}"
  ENV_ROOT="${ENV_ROOT:-/app/environment}"
  local table="${ENV_ROOT}/q2_auth/auth_table"
  local tag="2"
  while IFS=$'\t' read -r m t; do
    [[ -z "$m" || "$m" == \#* ]] && continue
    if [[ "$m" == "$mark" ]]; then
      tag="$t"
      break
    fi
  done < "$table"
  echo "$tag"
}
EOF

cat > /app/environment/q4_core/main_core.c <<'EOF'
#include "cap_layout.h"

#include <stddef.h>

int route_b(const cap_user_header_t *hdr, cap_flag_t flag)
{
    if (hdr == NULL) {
        return -1;
    }
    uint32_t eff = hdr->effective;
    uint32_t bnd = hdr->bound;
    if ((flag & CAP_FLAG_NNP) != 0) {
        bnd = (eff & 0xf0u) | (bnd & 0x0fu);
    } else {
        bnd = eff & 0xf0u;
    }
    return (int)bnd;
}
EOF

cat > /app/environment/q5_stage/pick_main.c <<'EOF'
#include "cap_layout.h"

#include <stddef.h>
#include <string.h>

int gate_c(const char *mark, unsigned stamp)
{
    (void)mark;
    (void)stamp;
    return 0x01;
}
EOF

cat > /app/environment/q7_launch/sync_path.sh <<'EOF'
#!/bin/bash
sync_d() {
  local mark="${1:-}"
  local round="${2:-}"
  local eff_pre="${3:-0}"
  local eff_post="${4:-0}"
  ENV_ROOT="${ENV_ROOT:-/app/environment}"
  local post_file="${ENV_ROOT}/fixtures/q8/post_step.dat"
  local gap="G0"
  local required="0x40"
  local expect_gap="G7"
  if [[ -f "$post_file" ]]; then
    required=$(grep '^required=' "$post_file" | cut -d= -f2)
    expect_gap=$(grep '^gap_code=' "$post_file" | cut -d= -f2)
  fi
  if [[ "$mark" == "wrapped_p1" && "$round" == "r1" ]]; then
    local post_mask=$((eff_post))
    local req_mask=$((required))
    if (( (post_mask & req_mask) == req_mask )); then
      gap="G0"
    else
      gap="$expect_gap"
    fi
  fi
  echo "$gap"
}
EOF

cat > /app/environment/q6_recover/merge_tail.sh <<'EOF'
#!/bin/bash
merge_tail() {
  ENV_ROOT="${ENV_ROOT:-/app/environment}"
  local journal="/app/work/cap_journal.tsv"
  local store="/app/work/cap_store.tsv"
  local best="/app/work/merge_best.tsv"
  local tmpstore="/app/work/cap_store.next.tsv"
  [[ -f "$journal" ]] || return 0
  awk -F'\t' '
    NF >= 10 {
      key = $2 SUBSEP $3 SUBSEP $4
      if (!(key in seq) || ($1 + 0) >= seq[key]) {
        seq[key] = $1 + 0
        line[key] = $2 "\t" $3 "\t" $4 "\t" $5 "\t" $6 "\t" $7 "\t" $8 "\t" $9 "\t" $10 "\t" $1
      }
    }
    END {
      for (k in line) print line[k]
    }
  ' "$journal" > "$best"
  if [[ ! -s "$best" ]]; then
    return 0
  fi
  awk -F'\t' -v bestfile="$best" '
    BEGIN {
      while ((getline row < bestfile) > 0) {
        split(row, f, "\t")
        drop[f[1] SUBSEP f[2] SUBSEP f[3]] = 1
      }
      close(bestfile)
    }
    {
      key = $1 SUBSEP $2 SUBSEP $3
      if (!(key in drop)) print $0
    }
  ' "$store" 2>/dev/null > "$tmpstore" || : > "$tmpstore"
  cat "$best" >> "$tmpstore"
  mv "$tmpstore" "$store"
}
EOF

cat > /app/environment/q4_core/chain_ambient.c <<'EOF'
#include "cap_layout.h"

#include <stddef.h>

int chain_ambient(uint32_t base, uint32_t ambient, uint32_t *out)
{
    if (out == NULL) {
        return -1;
    }
    *out = (base | ambient) & 0xffu;
    return 0;
}
EOF

cat > /app/environment/d0/cap_store.c <<'EOF'
#include "cap_store.h"
#include "cap_journal.h"

#include <stdio.h>
#include <string.h>

static cap_row_t g_rows[CAP_MAX_ROWS];
static int g_count = 0;

static const char *store_path(void)
{
    return "/app/work/cap_store.tsv";
}

int cap_store_clear(void)
{
    g_count = 0;
    return cap_store_save();
}

int cap_store_load(void)
{
    FILE *fp = fopen(store_path(), "r");
    g_count = 0;
    if (fp == NULL) {
        return 0;
    }
    char line[512];
    while (fgets(line, sizeof(line), fp) != NULL && g_count < CAP_MAX_ROWS) {
        cap_row_t row;
        memset(&row, 0, sizeof(row));
        if (sscanf(line, "%7s\t%15s\t%31s\t%d\t%15s\t%15s\t%7s\t%31s\t%u\t%u", row.round, row.actor,
                   row.mark, &row.class_tag, row.cap_effective, row.cap_bound, row.gap_code, row.launch_mark,
                   &row.stamp_code, &row.seq_code) < 10) {
            continue;
        }
        g_rows[g_count++] = row;
    }
    fclose(fp);
    return 0;
}

int cap_store_save(void)
{
    FILE *fp = fopen(store_path(), "w");
    if (fp == NULL) {
        return -1;
    }
    for (int i = 0; i < g_count; i++) {
        cap_row_t *row = &g_rows[i];
        (void)fprintf(fp, "%s\t%s\t%s\t%d\t%s\t%s\t%s\t%s\t%u\t%u\n", row->round, row->actor, row->mark,
                      row->class_tag, row->cap_effective, row->cap_bound, row->gap_code, row->launch_mark,
                      row->stamp_code, row->seq_code);
    }
    fclose(fp);
    return 0;
}

int cap_store_count(void)
{
    return g_count;
}

int cap_store_get(int index, cap_row_t *row)
{
    if (row == NULL || index < 0 || index >= g_count) {
        return -1;
    }
    *row = g_rows[index];
    return 0;
}

int cap_store_find(const char *round, const char *actor, const char *mark, cap_row_t *row)
{
    for (int i = g_count - 1; i >= 0; i--) {
        if (strcmp(g_rows[i].round, round) == 0 && strcmp(g_rows[i].actor, actor) == 0 &&
            strcmp(g_rows[i].mark, mark) == 0) {
            if (row != NULL) {
                *row = g_rows[i];
            }
            return 0;
        }
    }
    return -1;
}

static unsigned next_seq(const cap_row_t *row)
{
    unsigned tail = 0;
    (void)cap_journal_tail_seq(row->round, row->actor, row->mark, &tail);
    return tail + 1;
}

int cap_store_upsert(const cap_row_t *row)
{
    if (row == NULL) {
        return -1;
    }
    cap_row_t copy = *row;
    if (copy.seq_code == 0) {
        copy.seq_code = next_seq(&copy);
    }
    for (int i = 0; i < g_count; i++) {
        if (strcmp(g_rows[i].round, copy.round) == 0 && strcmp(g_rows[i].actor, copy.actor) == 0 &&
            strcmp(g_rows[i].mark, copy.mark) == 0) {
            g_rows[i] = copy;
            (void)cap_journal_append(&copy);
            return cap_store_save();
        }
    }
    if (g_count >= CAP_MAX_ROWS) {
        return -1;
    }
    g_rows[g_count++] = copy;
    (void)cap_journal_append(&copy);
    return cap_store_save();
}
EOF

cat > /app/environment/d0/cap_journal.c <<'EOF'
#include "cap_journal.h"

#include <stdio.h>
#include <string.h>

static const char *journal_path(void)
{
    return "/app/work/cap_journal.tsv";
}

int cap_journal_append(const cap_row_t *row)
{
    if (row == NULL) {
        return -1;
    }
    FILE *fp = fopen(journal_path(), "a");
    if (fp == NULL) {
        return -1;
    }
    (void)fprintf(fp, "%u\t%s\t%s\t%s\t%d\t%s\t%s\t%s\t%s\t%u\n", row->seq_code, row->round, row->actor, row->mark,
                  row->class_tag, row->cap_effective, row->cap_bound, row->gap_code, row->launch_mark,
                  row->stamp_code);
    fclose(fp);
    return 0;
}

int cap_journal_tail_seq(const char *round, const char *actor, const char *mark, unsigned *out_seq)
{
    if (round == NULL || actor == NULL || mark == NULL || out_seq == NULL) {
        return -1;
    }
    FILE *fp = fopen(journal_path(), "r");
    if (fp == NULL) {
        *out_seq = 0;
        return 0;
    }
    unsigned best = 0;
    char line[512];
    while (fgets(line, sizeof(line), fp) != NULL) {
        unsigned seq = 0;
        char r[8];
        char a[16];
        char m[32];
        if (sscanf(line, "%u\t%7s\t%15s\t%31s", &seq, r, a, m) < 4) {
            continue;
        }
        if (strcmp(r, round) == 0 && strcmp(a, actor) == 0 && strcmp(m, mark) == 0 && seq >= best) {
            best = seq;
        }
    }
    fclose(fp);
    *out_seq = best;
    return 0;
}
EOF

cat > /app/environment/d0/cap_replay.c <<'EOF'
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
        return;
    }
    cap_row_t prior;
    if (cap_store_find("r2", "b_two", "direct_r1", &prior) == 0) {
        uint32_t parsed = 0;
        if (sscanf(prior.cap_effective, "0x%x", &parsed) == 1) {
            *effective = parsed;
        }
        return;
    }
    (void)parse_hex_kv("/app/environment/fixtures/q8/r3_bridge.dat", "bridge_effective", effective);
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
    uint32_t ambient = 0u;
    (void)parse_hex_kv(actor_env, "BASE_EFFECTIVE", &effective);
    (void)parse_hex_kv(actor_env, "BASE_BOUND", &bound);
    (void)parse_hex_kv(actor_env, "AMBIENT_MASK", &ambient);
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
EOF

cat > /app/environment/d0/cap_emit.c <<'EOF'
#include "cap_layout.h"
#include "cap_store.h"
#include "sha256.h"

#include <stdio.h>
#include <string.h>

static void row_effective_hash(const cap_row_t *row, char out[65])
{
    char payload[512];
    (void)snprintf(payload, sizeof(payload),
                   "{\"actor\":\"%s\",\"cap_bound\":\"%s\",\"cap_effective\":\"%s\",\"class_tag\":%d,"
                   "\"mark\":\"%s\",\"round\":\"%s\"}",
                   row->actor, row->cap_bound, row->cap_effective, row->class_tag, row->mark, row->round);
    cap_sha256_hex((const uint8_t *)payload, strlen(payload), out);
}

static void row_bound_hash(const cap_row_t *row, char out[65])
{
    cap_sha256_hex((const uint8_t *)row->cap_bound, strlen(row->cap_bound), out);
}

static int row_cmp(const cap_row_t *a, const cap_row_t *b)
{
    int c = strcmp(a->round, b->round);
    if (c != 0) {
        return c;
    }
    c = strcmp(a->actor, b->actor);
    if (c != 0) {
        return c;
    }
    return strcmp(a->mark, b->mark);
}

static void bundle_digest(const cap_row_t *rows, int n, char out[65])
{
    char lines[CAP_MAX_ROWS][256];
    int count = 0;
    for (int i = 0; i < n; i++) {
        (void)snprintf(lines[count++], sizeof(lines[0]), "%s,%s,%s,%s,%s,%u", rows[i].round, rows[i].actor,
                       rows[i].mark, rows[i].effective_set_hash, rows[i].bound_set_hash, rows[i].seq_code);
    }
    for (int i = 0; i < count; i++) {
        for (int j = i + 1; j < count; j++) {
            if (strcmp(lines[i], lines[j]) > 0) {
                char tmp[256];
                (void)strncpy(tmp, lines[i], sizeof(tmp));
                (void)strncpy(lines[i], lines[j], sizeof(lines[i]));
                (void)strncpy(lines[j], tmp, sizeof(lines[j]));
            }
        }
    }
    char body[16384];
    size_t off = 0;
    for (int i = 0; i < count; i++) {
        int wrote = snprintf(body + off, sizeof(body) - off, "%s\n", lines[i]);
        if (wrote < 0) {
            return;
        }
        off += (size_t)wrote;
    }
    cap_sha256_hex((const uint8_t *)body, off, out);
}

int emit_cap_json(const char *out_path)
{
    cap_row_t rows[CAP_MAX_ROWS];
    int n = cap_store_count();
    for (int i = 0; i < n; i++) {
        if (cap_store_get(i, &rows[i]) != 0) {
            return -1;
        }
        row_effective_hash(&rows[i], rows[i].effective_set_hash);
        row_bound_hash(&rows[i], rows[i].bound_set_hash);
    }
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            if (row_cmp(&rows[i], &rows[j]) > 0) {
                cap_row_t tmp = rows[i];
                rows[i] = rows[j];
                rows[j] = tmp;
            }
        }
    }
    char digest[65];
    bundle_digest(rows, n, digest);
    FILE *out = fopen(out_path, "w");
    if (out == NULL) {
        return -1;
    }
    (void)fprintf(out, "{\n  \"bundle_digest\": \"%s\",\n  \"rows\": [\n", digest);
    int first = 1;
    for (int i = 0; i < n; i++) {
        cap_row_t *row = &rows[i];
        if (!first) {
            (void)fprintf(out, ",\n");
        }
        first = 0;
        (void)fprintf(out,
                      "    {\"round\": \"%s\", \"actor\": \"%s\", \"mark\": \"%s\", \"class_tag\": %d, "
                      "\"effective_set_hash\": \"%s\", \"bound_set_hash\": \"%s\", \"gap_code\": \"%s\", "
                      "\"launch_mark\": \"%s\", \"stamp_code\": %u, \"seq_code\": %u}",
                      row->round, row->actor, row->mark, row->class_tag, row->effective_set_hash, row->bound_set_hash,
                      row->gap_code, row->launch_mark, row->stamp_code, row->seq_code);
    }
    (void)fprintf(out, "\n  ]\n}\n");
    fclose(out);
    return 0;
}
EOF

cat > /app/environment/tools/m2_publish <<'EOF'
#!/bin/bash
set -euo pipefail
# Publish output path (m2_publish --out); see instruction.md and run_cli.md.
PUBLISH_OUT="/app/output/cap_audit.json"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) PUBLISH_OUT="$2"; shift 2 ;;
    --help|-h)
      echo "usage: m2_publish [--out /app/output/cap_audit.json]" >&2
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
mkdir -p /app/output /app/work
# shellcheck source=/app/environment/q6_recover/merge_tail.sh
source /app/environment/q6_recover/merge_tail.sh
merge_tail
exec /app/environment/d0/cap_drv emit --out "${PUBLISH_OUT}"
EOF

make -C /app/environment clean
make -C /app/environment all
chmod +x /app/environment/tools/m2_publish /app/environment/q6_recover/merge_tail.sh

mkdir -p /app/work /app/output
rm -f /app/output/cap_audit.json
find /app/work -mindepth 1 -delete 2>/dev/null || true

/app/environment/tools/k9_round --round r0 --actor a_one --mark wrap_r0 --launch sync
/app/environment/tools/k9_round --round r0 --actor a_one --mark direct_bypass --launch direct
/app/environment/tools/k9_round --round r1 --actor a_one --mark wrapped_p1 --launch sync
/app/environment/tools/k9_round --round r1 --actor a_one --mark direct_bypass --launch direct
/app/environment/tools/k9_round --round r2 --actor b_two --mark direct_r1 --launch direct
/app/environment/tools/k9_round --round r3 --actor c_three --mark wrapped_r2 --launch sync
/app/environment/tools/k9_round --round r3 --actor c_three --mark direct_r2 --launch direct
/app/environment/tools/m2_publish --out /app/output/cap_audit.json
test -s /app/output/cap_audit.json
