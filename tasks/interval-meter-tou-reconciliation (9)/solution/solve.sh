#!/bin/bash
set -euo pipefail

cat > /app/environment/src/main.c <<'C'
#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>

#define MAX_FIXTURES 512
#define MAX_ROWS 20000
#define MAX_METERS 1024
#define MAX_WINDOWS 64
#define STR 1024

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

typedef struct {
    int start_min;
    int end_min;
    int tier; /* 0 off, 1 mid, 2 on */
} Window;

typedef struct {
    char timezone[STR];
    double register_max_kwh;
    int interval_minutes;
    int summer_start;
    int summer_end;
    Window summer[MAX_WINDOWS];
    int n_summer;
    Window winter[MAX_WINDOWS];
    int n_winter;
} Tariff;

typedef struct {
    char name[STR];
    char csv[PATH_MAX];
} Fixture;

typedef struct {
    Tariff tariff;
    Fixture fixtures[MAX_FIXTURES];
    int fixture_count;
} RunConfig;

typedef struct {
    char meter_id[STR];
    char quality[64];
    double register_kwh;
    long long abs_ms;
    int year, month, day, hour, minute, second, millis;
    int offset_minutes;
    int seq;
} Row;

typedef struct {
    int interval_count;
    double total_kwh;
    double tiers[3];
    double demand_peak_kw;
    int rollover_events;
    int gap_intervals;
    int reconciled;
    double register_delta_kwh;
} Stats;

static char *read_file(const char *path) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return NULL;
    if (fseek(fp, 0, SEEK_END) != 0) { fclose(fp); return NULL; }
    long sz = ftell(fp);
    if (sz < 0) { fclose(fp); return NULL; }
    rewind(fp);
    char *buf = (char *)malloc((size_t)sz + 1);
    if (!buf) { fclose(fp); return NULL; }
    size_t got = fread(buf, 1, (size_t)sz, fp);
    buf[got] = '\0';
    fclose(fp);
    return buf;
}

static const char *find_key_range(const char *start, const char *end, const char *key) {
    char quoted[256];
    snprintf(quoted, sizeof(quoted), "\"%s\"", key);
    const char *p = start;
    while (p && (!end || p < end)) {
        const char *q = strstr(p, quoted);
        if (!q || (end && q >= end)) return NULL;
        return q;
    }
    return NULL;
}

static int parse_json_string_at(const char *quote, char *out, size_t cap, const char **after) {
    if (!quote || *quote != '"' || cap == 0) return -1;
    size_t n = 0;
    const char *p = quote + 1;
    while (*p && *p != '"') {
        char ch = *p++;
        if (ch == '\\') {
            ch = *p++;
            if (ch == 'n') ch = '\n';
            else if (ch == 'r') ch = '\r';
            else if (ch == 't') ch = '\t';
            else if (ch == 'b') ch = '\b';
            else if (ch == 'f') ch = '\f';
        }
        if (n + 1 < cap) out[n++] = ch;
    }
    if (*p != '"') return -1;
    out[n] = '\0';
    if (after) *after = p + 1;
    return 0;
}

static int json_get_string_range(const char *start, const char *end, const char *key, char *out, size_t cap) {
    const char *k = find_key_range(start, end, key);
    if (!k) return -1;
    const char *colon = strchr(k, ':');
    if (!colon || (end && colon >= end)) return -1;
    const char *q = strchr(colon, '"');
    if (!q || (end && q >= end)) return -1;
    return parse_json_string_at(q, out, cap, NULL);
}

static int json_get_double(const char *buf, const char *key, double *out) {
    const char *k = find_key_range(buf, NULL, key);
    if (!k) return -1;
    const char *colon = strchr(k, ':');
    if (!colon) return -1;
    char *endp = NULL;
    double v = strtod(colon + 1, &endp);
    if (endp == colon + 1) return -1;
    *out = v;
    return 0;
}

static int json_get_int(const char *buf, const char *key, int *out) {
    double v;
    if (json_get_double(buf, key, &v) != 0) return -1;
    *out = (int)llround(v);
    return 0;
}

static const char *match_bracket(const char *open, char left, char right) {
    int depth = 0;
    int in_str = 0;
    int esc = 0;
    for (const char *p = open; *p; p++) {
        if (in_str) {
            if (esc) esc = 0;
            else if (*p == '\\') esc = 1;
            else if (*p == '"') in_str = 0;
            continue;
        }
        if (*p == '"') { in_str = 1; continue; }
        if (*p == left) depth++;
        else if (*p == right) {
            depth--;
            if (depth == 0) return p;
        }
    }
    return NULL;
}

static int parse_clock(const char *s) {
    int h = 0, m = 0;
    if (sscanf(s, "%d:%d", &h, &m) != 2) return 0;
    return h * 60 + m;
}

static int parse_mmdd(const char *s) {
    int m = 0, d = 0;
    if (sscanf(s, "%d-%d", &m, &d) != 2) return 0;
    return m * 100 + d;
}

static void parse_tier_windows(const char *sec_start, const char *sec_end, const char *key, int tier, Window *out, int *count) {
    const char *k = find_key_range(sec_start, sec_end, key);
    if (!k) return;
    const char *colon = strchr(k, ':');
    if (!colon || colon >= sec_end) return;
    const char *arr = strchr(colon, '[');
    if (!arr || arr >= sec_end) return;
    const char *arr_end = match_bracket(arr, '[', ']');
    if (!arr_end || arr_end > sec_end) return;
    const char *p = arr;
    char a[32], b[32];
    while (p < arr_end) {
        const char *q1 = strchr(p, '"');
        if (!q1 || q1 >= arr_end) break;
        const char *after1 = NULL;
        if (parse_json_string_at(q1, a, sizeof(a), &after1) != 0) break;
        const char *q2 = strchr(after1, '"');
        if (!q2 || q2 >= arr_end) break;
        const char *after2 = NULL;
        if (parse_json_string_at(q2, b, sizeof(b), &after2) != 0) break;
        if (*count < MAX_WINDOWS) {
            out[*count].start_min = parse_clock(a);
            out[*count].end_min = parse_clock(b);
            out[*count].tier = tier;
            (*count)++;
        }
        p = after2;
    }
}

static void parse_season_windows(const char *buf, const char *season, Window *out, int *count) {
    *count = 0;
    const char *windows = find_key_range(buf, NULL, "windows");
    if (!windows) return;
    const char *skey = find_key_range(windows, NULL, season);
    if (!skey) return;
    const char *open = strchr(skey, '{');
    if (!open) return;
    const char *close = match_bracket(open, '{', '}');
    if (!close) return;
    parse_tier_windows(open, close, "off_peak", 0, out, count);
    parse_tier_windows(open, close, "mid_peak", 1, out, count);
    parse_tier_windows(open, close, "on_peak", 2, out, count);
}

static int load_tariff(const char *path, Tariff *t) {
    memset(t, 0, sizeof(*t));
    strcpy(t->timezone, "America/Chicago");
    t->register_max_kwh = 99999.999;
    t->interval_minutes = 15;
    t->summer_start = 601;
    t->summer_end = 930;
    char *buf = read_file(path);
    if (!buf) return -1;
    json_get_string_range(buf, NULL, "timezone", t->timezone, sizeof(t->timezone));
    json_get_double(buf, "register_max_kwh", &t->register_max_kwh);
    json_get_int(buf, "interval_minutes", &t->interval_minutes);

    const char *seasons = find_key_range(buf, NULL, "seasons");
    if (seasons) {
        const char *summer = find_key_range(seasons, NULL, "summer");
        if (summer) {
            const char *open = strchr(summer, '{');
            const char *close = open ? match_bracket(open, '{', '}') : NULL;
            char mmdd[32];
            if (open && close && json_get_string_range(open, close, "start_mmdd", mmdd, sizeof(mmdd)) == 0) t->summer_start = parse_mmdd(mmdd);
            if (open && close && json_get_string_range(open, close, "end_mmdd", mmdd, sizeof(mmdd)) == 0) t->summer_end = parse_mmdd(mmdd);
        }
    }
    parse_season_windows(buf, "summer", t->summer, &t->n_summer);
    parse_season_windows(buf, "winter", t->winter, &t->n_winter);
    free(buf);
    return 0;
}

static int load_run_config(const char *path, RunConfig *cfg) {
    memset(cfg, 0, sizeof(*cfg));
    char *buf = read_file(path);
    if (!buf) return -1;
    char tariff_path[PATH_MAX] = "/app/environment/config/tariffs.json";
    json_get_string_range(buf, NULL, "tariff_path", tariff_path, sizeof(tariff_path));
    if (load_tariff(tariff_path, &cfg->tariff) != 0) { free(buf); return -1; }

    const char *fs = find_key_range(buf, NULL, "fixture_sets");
    if (!fs) { free(buf); return -1; }
    const char *arr = strchr(fs, '[');
    const char *arr_end = arr ? match_bracket(arr, '[', ']') : NULL;
    if (!arr || !arr_end) { free(buf); return -1; }
    const char *cur = arr + 1;
    while (cur < arr_end && cfg->fixture_count < MAX_FIXTURES) {
        const char *obj = strchr(cur, '{');
        if (!obj || obj >= arr_end) break;
        const char *obj_end = match_bracket(obj, '{', '}');
        if (!obj_end || obj_end > arr_end) break;
        Fixture *fx = &cfg->fixtures[cfg->fixture_count];
        if (json_get_string_range(obj, obj_end, "name", fx->name, sizeof(fx->name)) == 0 &&
            json_get_string_range(obj, obj_end, "csv", fx->csv, sizeof(fx->csv)) == 0) {
            cfg->fixture_count++;
        }
        cur = obj_end + 1;
    }
    free(buf);
    return cfg->fixture_count > 0 ? 0 : -1;
}

static long long days_from_civil(int y, unsigned m, unsigned d) {
    y -= m <= 2;
    const int era = (y >= 0 ? y : y - 399) / 400;
    const unsigned yoe = (unsigned)(y - era * 400);
    const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097LL + (long long)doe - 719468LL;
}

static void civil_from_days(long long z, int *y, int *m, int *d) {
    z += 719468LL;
    const long long era = (z >= 0 ? z : z - 146096LL) / 146097LL;
    const unsigned doe = (unsigned)(z - era * 146097LL);
    const unsigned yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    long long yy = (long long)yoe + era * 400LL;
    const unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    const unsigned mp = (5 * doy + 2) / 153;
    const unsigned dd = doy - (153 * mp + 2) / 5 + 1;
    const unsigned mm = mp + (mp < 10 ? 3 : -9);
    yy += (mm <= 2);
    *y = (int)yy; *m = (int)mm; *d = (int)dd;
}

static long long floor_div_ll(long long a, long long b) {
    long long q = a / b;
    long long r = a % b;
    if (r != 0 && ((r > 0) != (b > 0))) q--;
    return q;
}

static long long local_epoch_ms_from_parts(int y, int m, int d, int hh, int mm, int ss, int ms) {
    long long days = days_from_civil(y, (unsigned)m, (unsigned)d);
    return (((days * 24LL + hh) * 60LL + mm) * 60LL + ss) * 1000LL + ms;
}

static void parts_from_local_epoch_ms(long long ms, int *y, int *m, int *d, int *hh, int *mi, int *ss) {
    long long sec = floor_div_ll(ms, 1000LL);
    long long days = floor_div_ll(sec, 86400LL);
    long long rem = sec - days * 86400LL;
    if (rem < 0) { rem += 86400LL; days--; }
    civil_from_days(days, y, m, d);
    *hh = (int)(rem / 3600LL);
    rem %= 3600LL;
    *mi = (int)(rem / 60LL);
    *ss = (int)(rem % 60LL);
}

static int parse_timestamp_row(const char *iso, Row *row) {
    int y=0, mo=0, d=0, h=0, mi=0;
    double secd=0.0;
    int pos=0;
    if (sscanf(iso, "%d-%d-%dT%d:%d:%lf%n", &y, &mo, &d, &h, &mi, &secd, &pos) != 6) return -1;
    int sec = (int)floor(secd + 1e-9);
    int ms = (int)llround((secd - sec) * 1000.0);
    if (ms >= 1000) { sec += 1; ms -= 1000; }
    const char *p = iso + pos;
    int off_min = 0;
    if (*p == 'Z') {
        off_min = 0;
    } else if (*p == '+' || *p == '-') {
        int sign = (*p == '-') ? -1 : 1;
        int oh=0, om=0;
        if (sscanf(p + 1, "%d:%d", &oh, &om) != 2) return -1;
        off_min = sign * (oh * 60 + om);
    } else {
        return -1;
    }
    row->year = y; row->month = mo; row->day = d; row->hour = h; row->minute = mi; row->second = sec; row->millis = ms;
    row->offset_minutes = off_min;
    long long local_ms = local_epoch_ms_from_parts(y, mo, d, h, mi, sec, ms);
    row->abs_ms = local_ms - (long long)off_min * 60LL * 1000LL;
    return 0;
}

static void trim(char *s) {
    size_t n = strlen(s);
    while (n > 0 && (s[n-1] == '\n' || s[n-1] == '\r' || isspace((unsigned char)s[n-1]))) s[--n] = '\0';
    size_t i = 0;
    while (s[i] && isspace((unsigned char)s[i])) i++;
    if (i) memmove(s, s+i, strlen(s+i)+1);
}

static int parse_csv_line(const char *line, char fields[][STR], int max_fields) {
    int f = 0;
    size_t n = 0;
    int in_quotes = 0;
    const char *p = line;
    if (max_fields <= 0) return 0;
    fields[0][0] = '\0';
    while (*p && *p != '\n' && *p != '\r') {
        char ch = *p++;
        if (in_quotes) {
            if (ch == '"') {
                if (*p == '"') {
                    if (n + 1 < STR) fields[f][n++] = '"';
                    p++;
                } else {
                    in_quotes = 0;
                }
            } else {
                if (n + 1 < STR) fields[f][n++] = ch;
            }
        } else {
            if (ch == '"' && n == 0) {
                in_quotes = 1;
            } else if (ch == ',') {
                fields[f][n] = '\0';
                trim(fields[f]);
                f++;
                if (f >= max_fields) return f;
                n = 0;
                fields[f][0] = '\0';
            } else {
                if (n + 1 < STR) fields[f][n++] = ch;
            }
        }
    }
    fields[f][n] = '\0';
    trim(fields[f]);
    return f + 1;
}

static void lower_inplace(char *s) {
    for (; *s; s++) *s = (char)tolower((unsigned char)*s);
}

static int load_csv_rows(const char *path, Row *rows, int *out_count) {
    FILE *fp = fopen(path, "r");
    if (!fp) return -1;
    char line[4096];
    if (!fgets(line, sizeof(line), fp)) { fclose(fp); return -1; }
    char header[8][STR];
    int hcount = parse_csv_line(line, header, 8);
    int meter_col=-1, ts_col=-1, reg_col=-1, qual_col=-1;
    for (int i=0; i<hcount; i++) {
        lower_inplace(header[i]);
        if (strcmp(header[i], "meter_id") == 0) meter_col = i;
        else if (strcmp(header[i], "timestamp") == 0) ts_col = i;
        else if (strcmp(header[i], "register_kwh") == 0) reg_col = i;
        else if (strcmp(header[i], "quality") == 0 || strcmp(header[i], "quality_code") == 0) qual_col = i;
    }
    if (meter_col < 0 || ts_col < 0 || reg_col < 0) { fclose(fp); return -1; }
    int count = 0, seq = 0;
    while (fgets(line, sizeof(line), fp)) {
        char fields[8][STR];
        int c = parse_csv_line(line, fields, 8);
        if (c <= reg_col) continue;
        char quality[64] = "actual";
        if (qual_col >= 0 && qual_col < c) {
            strncpy(quality, fields[qual_col], sizeof(quality)-1);
            quality[sizeof(quality)-1] = '\0';
            trim(quality);
            lower_inplace(quality);
            if (quality[0] == '\0') strcpy(quality, "actual");
            if (strcmp(quality, "estimated") == 0) strcpy(quality, "estimate");
        }
        if (strcmp(quality, "void") == 0) {
            seq++;
            continue;
        }
        if (count >= MAX_ROWS) { fclose(fp); return -1; }
        Row *r = &rows[count];
        memset(r, 0, sizeof(*r));
        strncpy(r->meter_id, fields[meter_col], sizeof(r->meter_id)-1);
        strncpy(r->quality, quality, sizeof(r->quality)-1);
        r->register_kwh = strtod(fields[reg_col], NULL);
        r->seq = seq++;
        if (parse_timestamp_row(fields[ts_col], r) != 0) { fclose(fp); return -1; }
        count++;
    }
    fclose(fp);
    *out_count = count;
    return 0;
}

static int row_cmp(const void *a, const void *b) {
    const Row *ra = (const Row *)a;
    const Row *rb = (const Row *)b;
    int m = strcmp(ra->meter_id, rb->meter_id);
    if (m != 0) return m;
    if (ra->abs_ms < rb->abs_ms) return -1;
    if (ra->abs_ms > rb->abs_ms) return 1;
    return (ra->seq > rb->seq) - (ra->seq < rb->seq);
}

static int is_summer_parts(int month, int day, const Tariff *t) {
    int mmdd = month * 100 + day;
    if (t->summer_start <= t->summer_end) return mmdd >= t->summer_start && mmdd <= t->summer_end;
    return mmdd >= t->summer_start || mmdd <= t->summer_end;
}

static int minute_in_window(int minute, int start, int end) {
    if (start < end) return minute >= start && minute < end;
    return minute >= start || minute < end;
}

static int tier_for_slot(const Tariff *t, int year, int month, int day, int hour, int minute) {
    (void)year;
    const Window *w = is_summer_parts(month, day, t) ? t->summer : t->winter;
    int n = is_summer_parts(month, day, t) ? t->n_summer : t->n_winter;
    int clock = hour * 60 + minute;
    for (int i=0; i<n; i++) {
        if (minute_in_window(clock, w[i].start_min, w[i].end_min)) return w[i].tier;
    }
    return 0;
}

static int slots_between(const Row *prev, const Row *curr, const Tariff *t) {
    long long diff_ms = curr->abs_ms - prev->abs_ms;
    if (diff_ms <= 0) return 1;
    long long slot_ms = (long long)t->interval_minutes * 60LL * 1000LL;
    int slots = (int)(diff_ms / slot_ms);
    if (slots < 1) slots = 1;
    return slots;
}

static void add_slot_tier_overlap(const Tariff *t, long long seg_abs_start, long long seg_abs_end,
                                  long long prev_abs_ms, long long base_local_ms,
                                  double slot_kwh, Stats *st) {
    long long span_ms = seg_abs_end - seg_abs_start;
    if (span_ms <= 0) return;
    long long cur = seg_abs_start;
    while (cur < seg_abs_end) {
        long long local_ms = base_local_ms + (cur - prev_abs_ms);
        long long local_min_start = floor_div_ll(local_ms, 60000LL) * 60000LL;
        long long next_local_min = local_min_start + 60000LL;
        if (next_local_min <= local_ms) next_local_min += 60000LL;
        long long next_abs = prev_abs_ms + (next_local_min - base_local_ms);
        if (next_abs > seg_abs_end) next_abs = seg_abs_end;
        if (next_abs <= cur) next_abs = seg_abs_end;
        int y, mo, d, h, mi, se;
        parts_from_local_epoch_ms(local_ms, &y, &mo, &d, &h, &mi, &se);
        int tier = tier_for_slot(t, y, mo, d, h, mi);
        if (tier < 0 || tier > 2) tier = 0;
        st->tiers[tier] += slot_kwh * ((double)(next_abs - cur) / (double)span_ms);
        cur = next_abs;
    }
}

static void aggregate_rows(const Row *rows, int start, int end, const Tariff *t, Stats *st) {
    memset(st, 0, sizeof(*st));
    int have = 0;
    int used_estimate = 0;
    Row prev;
    memset(&prev, 0, sizeof(prev));
    for (int i=start; i<end; i++) {
        const Row *r = &rows[i];
        if (strcmp(r->quality, "reset") == 0) {
            prev = *r;
            have = 1;
            continue;
        }
        if (!have) {
            prev = *r;
            have = 1;
            if (strcmp(r->quality, "estimate") == 0) used_estimate = 1;
            continue;
        }
        if (r->abs_ms == prev.abs_ms) {
            prev = *r;
            continue;
        }
        double delta = r->register_kwh - prev.register_kwh;
        if (delta < 0.0) {
            st->rollover_events += 1;
            delta = (t->register_max_kwh - prev.register_kwh) + r->register_kwh;
        }
        int slots = slots_between(&prev, r, t);
        st->gap_intervals += slots > 0 ? slots - 1 : 0;
        st->interval_count += 1;
        st->total_kwh += delta;
        st->register_delta_kwh += delta;
        double per_slot = delta / (double)slots;
        long long base_local_ms = local_epoch_ms_from_parts(prev.year, prev.month, prev.day, prev.hour, prev.minute, prev.second, prev.millis);
        long long slot_ms = (long long)t->interval_minutes * 60LL * 1000LL;
        for (int s=0; s<slots; s++) {
            long long slot_abs_start = prev.abs_ms + (long long)s * slot_ms;
            long long slot_abs_end = prev.abs_ms + (long long)(s + 1) * slot_ms;
            if (slot_abs_end > r->abs_ms) slot_abs_end = r->abs_ms;
            add_slot_tier_overlap(t, slot_abs_start, slot_abs_end, prev.abs_ms, base_local_ms, per_slot, st);
            double kw = per_slot * 60.0 / (double)t->interval_minutes;
            if (kw > st->demand_peak_kw) st->demand_peak_kw = kw;
        }
        if (strcmp(r->quality, "estimate") == 0 || strcmp(prev.quality, "estimate") == 0) used_estimate = 1;
        prev = *r;
    }
    st->reconciled = (!used_estimate && fabs(st->total_kwh - st->register_delta_kwh) < 0.001) ? 1 : 0;
}

static void json_escape(FILE *fp, const char *s) {
    fputc('"', fp);
    for (; *s; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '"') fputs("\\\"", fp);
        else if (c == '\\') fputs("\\\\", fp);
        else if (c == '\n') fputs("\\n", fp);
        else if (c == '\r') fputs("\\r", fp);
        else if (c == '\t') fputs("\\t", fp);
        else if (c < 32) fprintf(fp, "\\u%04x", c);
        else fputc(c, fp);
    }
    fputc('"', fp);
}

static const char *tier_key(int tier) {
    return tier == 0 ? "off_peak" : tier == 1 ? "mid_peak" : "on_peak";
}

static void ensure_parent_dir(const char *path) {
    char tmp[PATH_MAX];
    strncpy(tmp, path, sizeof(tmp)-1);
    tmp[sizeof(tmp)-1] = '\0';
    for (char *p = tmp + 1; *p; p++) {
        if (*p == '/') {
            *p = '\0';
            mkdir(tmp, 0777);
            *p = '/';
        }
    }
}

static int write_report(const RunConfig *cfg, const char *out_path) {
    ensure_parent_dir(out_path);
    FILE *fp = fopen(out_path, "w");
    if (!fp) return -1;
    int all_reconciled = 1;

    typedef struct { char id[STR]; Stats st; } MeterOut;
    MeterOut *all_meters[MAX_FIXTURES];
    int meter_counts[MAX_FIXTURES];
    memset(all_meters, 0, sizeof(all_meters));
    memset(meter_counts, 0, sizeof(meter_counts));

    for (int f=0; f<cfg->fixture_count; f++) {
        Row *rows = (Row *)calloc(MAX_ROWS, sizeof(Row));
        if (!rows) { fclose(fp); return -1; }
        int nrows = 0;
        if (load_csv_rows(cfg->fixtures[f].csv, rows, &nrows) != 0) {
            free(rows); fclose(fp); return -1;
        }
        qsort(rows, (size_t)nrows, sizeof(Row), row_cmp);
        MeterOut *meters = (MeterOut *)calloc(MAX_METERS, sizeof(MeterOut));
        if (!meters) { free(rows); fclose(fp); return -1; }
        int mc = 0;
        int i = 0;
        while (i < nrows && mc < MAX_METERS) {
            int j = i + 1;
            while (j < nrows && strcmp(rows[j].meter_id, rows[i].meter_id) == 0) j++;
            strncpy(meters[mc].id, rows[i].meter_id, sizeof(meters[mc].id)-1);
            aggregate_rows(rows, i, j, &cfg->tariff, &meters[mc].st);
            if (!meters[mc].st.reconciled) all_reconciled = 0;
            mc++;
            i = j;
        }
        all_meters[f] = meters;
        meter_counts[f] = mc;
        free(rows);
    }

    fprintf(fp, "{\n  \"timezone\": ");
    json_escape(fp, cfg->tariff.timezone);
    fprintf(fp, ",\n  \"all_reconciled\": %s,\n  \"fixture_sets\": [\n", all_reconciled ? "true" : "false");
    for (int f=0; f<cfg->fixture_count; f++) {
        fprintf(fp, "    {\n      \"name\": ");
        json_escape(fp, cfg->fixtures[f].name);
        fprintf(fp, ",\n      \"meters\": {\n");
        for (int m=0; m<meter_counts[f]; m++) {
            MeterOut *mo = &all_meters[f][m];
            fprintf(fp, "        "); json_escape(fp, mo->id); fprintf(fp, ": {\n");
            fprintf(fp, "          \"interval_count\": %d,\n", mo->st.interval_count);
            fprintf(fp, "          \"total_kwh\": %.3f,\n", mo->st.total_kwh);
            fprintf(fp, "          \"tier_kwh\": {\n");
            fprintf(fp, "            \"%s\": %.3f,\n", tier_key(0), mo->st.tiers[0]);
            fprintf(fp, "            \"%s\": %.3f,\n", tier_key(1), mo->st.tiers[1]);
            fprintf(fp, "            \"%s\": %.3f\n", tier_key(2), mo->st.tiers[2]);
            fprintf(fp, "          },\n");
            fprintf(fp, "          \"demand_peak_kw\": %.3f,\n", mo->st.demand_peak_kw);
            fprintf(fp, "          \"rollover_events\": %d,\n", mo->st.rollover_events);
            fprintf(fp, "          \"gap_intervals\": %d,\n", mo->st.gap_intervals);
            fprintf(fp, "          \"reconciled\": %s,\n", mo->st.reconciled ? "true" : "false");
            fprintf(fp, "          \"register_delta_kwh\": %.3f\n", mo->st.register_delta_kwh);
            fprintf(fp, "        }%s\n", (m + 1 < meter_counts[f]) ? "," : "");
        }
        fprintf(fp, "      }\n    }%s\n", (f + 1 < cfg->fixture_count) ? "," : "");
        free(all_meters[f]);
    }
    fprintf(fp, "  ]\n}\n");
    fclose(fp);
    return 0;
}

int main(int argc, char **argv) {
    const char *config_path = "/app/environment/config/run.json";
    const char *out_path = "/app/output/reconciliation_report.json";
    for (int i=1; i<argc; i++) {
        if (strcmp(argv[i], "--config") == 0 && i + 1 < argc) config_path = argv[++i];
        else if (strcmp(argv[i], "--out") == 0 && i + 1 < argc) out_path = argv[++i];
    }
    RunConfig cfg;
    if (load_run_config(config_path, &cfg) != 0) {
        fprintf(stderr, "failed to load config\n");
        return 1;
    }
    if (write_report(&cfg, out_path) != 0) {
        fprintf(stderr, "failed to write report\n");
        return 1;
    }
    return 0;
}
C

cat > /app/environment/Makefile <<'EOF'
CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -O2 -I/app/environment/include -I/app/environment/src
LDFLAGS = -lm

all: /app/bin/tou_reconcile

/app/bin/tou_reconcile: src/main.c
	mkdir -p /app/bin /app/output
	$(CC) $(CFLAGS) -o $@ src/main.c $(LDFLAGS)

clean:
	rm -f /app/bin/tou_reconcile

.PHONY: all clean
EOF

make -C /app/environment
/app/bin/tou_reconcile --config /app/environment/config/run.json --out /app/output/reconciliation_report.json
