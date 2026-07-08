#define _GNU_SOURCE
#include "ledger_verify.h"

#include <ctype.h>
#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <openssl/pem.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <unicode/unorm2.h>
#include <unicode/ustring.h>
#include <unicode/utypes.h>

#define FIELD_COUNT 6

typedef struct {
    char seq[32];
    char tenant[128];
    char amount[32];
    char memo[512];
    char posted_at[64];
    char signer[64];
} LedgerFields;

static void trim_inplace(char *s) {
    size_t len = strlen(s);
    while (len > 0 && isspace((unsigned char)s[len - 1])) {
        s[--len] = '\0';
    }
    char *start = s;
    while (*start && isspace((unsigned char)*start)) {
        start++;
    }
    if (start != s) {
        memmove(s, start, strlen(start) + 1);
    }
}

static void collapse_spaces(char *s) {
    char *out = s;
    int in_space = 0;
    for (char *p = s; *p; p++) {
        if (isspace((unsigned char)*p)) {
            if (!in_space) {
                *out++ = ' ';
                in_space = 1;
            }
        } else {
            *out++ = *p;
            in_space = 0;
        }
    }
    *out = '\0';
    trim_inplace(s);
}

static int utf8_to_nfc(const char *input, char *output, size_t out_len) {
    UChar src[1024];
    UChar dest[1024];
    UErrorCode status = U_ZERO_ERROR;
    int32_t src_len = 0;
    u_strFromUTF8(src, 1024, &src_len, input, -1, &status);
    if (U_FAILURE(status)) {
        return -1;
    }
    const UNormalizer2 *norm = unorm2_getNFCInstance(&status);
    if (U_FAILURE(status)) {
        return -1;
    }
    int32_t dest_len = unorm2_normalize(norm, src, src_len, dest, 1024, &status);
    if (U_FAILURE(status)) {
        return -1;
    }
    u_strToUTF8(output, (int32_t)out_len, NULL, dest, dest_len, &status);
    if (U_FAILURE(status)) {
        return -1;
    }
    return 0;
}

static void normalize_memo(const char *raw, char *out, size_t out_len) {
    char tmp[512];
    strncpy(tmp, raw, sizeof(tmp) - 1);
    tmp[sizeof(tmp) - 1] = '\0';
    trim_inplace(tmp);
    collapse_spaces(tmp);
    char nfc[512];
    if (utf8_to_nfc(tmp, nfc, sizeof(nfc)) != 0) {
        strncpy(nfc, tmp, sizeof(nfc) - 1);
        nfc[sizeof(nfc) - 1] = '\0';
    }
    if (nfc[0] == '\0') {
        strncpy(out, "(empty)", out_len - 1);
    } else {
        strncpy(out, nfc, out_len - 1);
    }
    out[out_len - 1] = '\0';
}

static void normalize_amount(const char *raw, char *out, size_t out_len) {
    long value = strtol(raw, NULL, 10);
    snprintf(out, out_len, "%ld", value);
}

static int parse_offset_minutes(const char *offset, int *minutes_out) {
    int sign = 1;
    if (*offset == '+') {
        offset++;
    } else if (*offset == '-') {
        sign = -1;
        offset++;
    }
    int hours = 0;
    int minutes = 0;
    if (strchr(offset, ':')) {
        if (sscanf(offset, "%d:%d", &hours, &minutes) != 2) {
            return -1;
        }
    } else if (sscanf(offset, "%2d%2d", &hours, &minutes) != 2) {
        return -1;
    }
    *minutes_out = sign * (hours * 60 + minutes);
    return 0;
}

static int normalize_posted_at(const char *raw, char *out, size_t out_len) {
    char buf[64];
    strncpy(buf, raw, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';
    trim_inplace(buf);

    int offset_minutes = 0;
    char *z = strchr(buf, 'Z');
    char *plus = strrchr(buf, '+');
    char *minus = strrchr(buf, '-');
    char *offset_ptr = NULL;
    if (z) {
        *z = '\0';
    } else if (plus && plus > strchr(buf, 'T')) {
        offset_ptr = plus;
    } else if (minus && minus > strchr(buf, 'T')) {
        offset_ptr = minus;
    }
    if (offset_ptr) {
        if (parse_offset_minutes(offset_ptr, &offset_minutes) != 0) {
            return -1;
        }
        *offset_ptr = '\0';
    }

    int year, month, day, hour, minute, second;
    if (sscanf(buf, "%d-%d-%dT%d:%d:%d", &year, &month, &day, &hour, &minute, &second) != 6) {
        return -1;
    }

    time_t epoch = timegm(&(struct tm){.tm_year = year - 1900,
                                       .tm_mon = month - 1,
                                       .tm_mday = day,
                                       .tm_hour = hour,
                                       .tm_min = minute,
                                       .tm_sec = second});
    if (epoch == (time_t)-1) {
        return -1;
    }
    epoch -= (time_t)offset_minutes * 60;

    struct tm utc;
    gmtime_r(&epoch, &utc);
    snprintf(out, out_len, "%04d-%02d-%02dT%02d:%02d:%02dZ",
             utc.tm_year + 1900, utc.tm_mon + 1, utc.tm_mday,
             utc.tm_hour, utc.tm_min, utc.tm_sec);
    return 0;
}

static int parse_csv_row(const char *csv_row, LedgerFields *fields) {
    char buf[2048];
    strncpy(buf, csv_row, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';

    char *values[7];
    int count = 0;
    char *cursor = buf;
    while (count < 7) {
        values[count++] = cursor;
        char *comma = strchr(cursor, ',');
        if (!comma) {
            break;
        }
        *comma = '\0';
        cursor = comma + 1;
    }
    if (count < 7) {
        return -1;
    }

    strncpy(fields->seq, values[0], sizeof(fields->seq) - 1);
    strncpy(fields->tenant, values[1], sizeof(fields->tenant) - 1);
    strncpy(fields->amount, values[2], sizeof(fields->amount) - 1);
    strncpy(fields->memo, values[3], sizeof(fields->memo) - 1);
    strncpy(fields->posted_at, values[4], sizeof(fields->posted_at) - 1);
    strncpy(fields->signer, values[5], sizeof(fields->signer) - 1);
    return 0;
}

static int compare_iso8601_utc(const char *a, const char *b) {
    return strcmp(a, b);
}

int ledger_canonicalize_row(const char *csv_row, char *out, size_t out_len) {
    LedgerFields fields;
    if (parse_csv_row(csv_row, &fields) != 0) {
        return -1;
    }

    char memo[512];
    char amount[32];
    char posted_at[64];
    normalize_memo(fields.memo, memo, sizeof(memo));
    normalize_amount(fields.amount, amount, sizeof(amount));
    if (normalize_posted_at(fields.posted_at, posted_at, sizeof(posted_at)) != 0) {
        return -1;
    }

    int n = snprintf(out, out_len, "%s|%s|%s|%s|%s|%s",
                     fields.seq, fields.tenant, amount, memo, posted_at, fields.signer);
    return n > 0 && (size_t)n < out_len ? 0 : -1;
}

static int hex_to_bytes(const char *hex, unsigned char *out, size_t out_len) {
    size_t hex_len = strlen(hex);
    if (hex_len / 2 > out_len) {
        return -1;
    }
    for (size_t i = 0; i < hex_len / 2; i++) {
        unsigned int byte = 0;
        if (sscanf(hex + i * 2, "%2x", &byte) != 1) {
            return -1;
        }
        out[i] = (unsigned char)byte;
    }
    return (int)(hex_len / 2);
}

static int load_public_key(const char *path, EVP_PKEY **pkey_out) {
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        return -1;
    }
    *pkey_out = PEM_read_PUBKEY(fp, NULL, NULL, NULL);
    fclose(fp);
    return *pkey_out ? 0 : -1;
}

static int verify_ed25519(const char *canonical, const char *sig_hex, const char *pub_pem_path) {
    unsigned char sig[128];
    int sig_len = hex_to_bytes(sig_hex, sig, sizeof(sig));
    if (sig_len <= 0) {
        return -1;
    }

    EVP_PKEY *pkey = NULL;
    if (load_public_key(pub_pem_path, &pkey) != 0) {
        return -1;
    }

    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    if (!ctx) {
        EVP_PKEY_free(pkey);
        return -1;
    }

    int ok = EVP_DigestVerifyInit(ctx, NULL, NULL, NULL, pkey) == 1
        && EVP_DigestVerify(ctx, sig, (size_t)sig_len,
                            (const unsigned char *)canonical, strlen(canonical)) == 1;

    EVP_MD_CTX_free(ctx);
    EVP_PKEY_free(pkey);
    return ok ? 0 : -1;
}

static int verify_hmac(const char *canonical, const char *sig_hex) {
    unsigned char expected[EVP_MAX_MD_SIZE];
    unsigned int expected_len = 0;

    FILE *fp = fopen("/app/data/ceremony_seed.bin", "rb");
    if (!fp) {
        return -1;
    }
    unsigned char seed[64];
    size_t seed_len = fread(seed, 1, sizeof(seed), fp);
    fclose(fp);
    if (seed_len == 0) {
        return -1;
    }

    HMAC(EVP_sha256(), seed, (int)seed_len,
         (const unsigned char *)canonical, strlen(canonical),
         expected, &expected_len);

    char expected_hex[128];
    for (unsigned int i = 0; i < expected_len; i++) {
        sprintf(expected_hex + i * 2, "%02x", expected[i]);
    }
    expected_hex[expected_len * 2] = '\0';
    return strcmp(expected_hex, sig_hex) == 0 ? 0 : -1;
}

static const char *select_public_key_path(const char *posted_at_utc) {
    if (compare_iso8601_utc(posted_at_utc, "2026-03-01T00:00:00Z") >= 0) {
        return "/app/data/keys/ledger-key-v2.pub.pem";
    }
    return "/app/data/keys/ledger-key-v1.pub.pem";
}

int ledger_verify_signature(
    const char *canonical,
    const char *sig_hex,
    const char *signer,
    const char *posted_at
) {
    char posted_at_utc[64];
    if (normalize_posted_at(posted_at, posted_at_utc, sizeof(posted_at_utc)) != 0) {
        return -1;
    }

    if (strcmp(signer, "legacy-bootstrap") == 0) {
        if (compare_iso8601_utc(posted_at_utc, "2026-03-15T00:00:00Z") > 0) {
            return -1;
        }
        return verify_hmac(canonical, sig_hex);
    }

    return verify_ed25519(canonical, sig_hex, select_public_key_path(posted_at_utc));
}

int ledger_row_digest(const char *canonical, const char *sig_hex, char *out, size_t out_len) {
    char payload[4096];
    int n = snprintf(payload, sizeof(payload), "%s|%s", canonical, sig_hex);
    if (n <= 0 || (size_t)n >= sizeof(payload)) {
        return -1;
    }

    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int digest_len = 0;
    EVP_Digest(payload, strlen(payload), digest, &digest_len, EVP_sha256(), NULL);
    for (unsigned int i = 0; i < digest_len; i++) {
        if (i * 2 + 2 >= out_len) {
            return -1;
        }
        sprintf(out + i * 2, "%02x", digest[i]);
    }
    out[digest_len * 2] = '\0';
    return 0;
}

int ledger_compute_chain_root(const char **row_digests, size_t count, char *root_hex, size_t root_len) {
    unsigned char state[EVP_MAX_MD_SIZE];
    unsigned int state_len = 0;
    EVP_Digest("ledger-genesis-v3", 17, state, &state_len, EVP_sha256(), NULL);

    char prev_hex[128];
    for (unsigned int i = 0; i < state_len; i++) {
        sprintf(prev_hex + i * 2, "%02x", state[i]);
    }
    prev_hex[state_len * 2] = '\0';

    for (size_t i = 0; i < count; i++) {
        char link[256];
        snprintf(link, sizeof(link), "%s|%s", prev_hex, row_digests[i]);
        EVP_Digest(link, strlen(link), state, &state_len, EVP_sha256(), NULL);
        for (unsigned int j = 0; j < state_len; j++) {
            sprintf(prev_hex + j * 2, "%02x", state[j]);
        }
        prev_hex[state_len * 2] = '\0';
    }

    strncpy(root_hex, prev_hex, root_len - 1);
    root_hex[root_len - 1] = '\0';
    return 0;
}
