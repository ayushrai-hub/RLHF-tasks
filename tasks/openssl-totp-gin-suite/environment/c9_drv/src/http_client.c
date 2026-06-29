#include "k9.h"

#include <curl/curl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct curl_buf {
    char *data;
    size_t len;
    size_t cap;
};

static size_t curl_write(void *ptr, size_t size, size_t nmemb, void *userdata) {
    struct curl_buf *buf = userdata;
    size_t total = size * nmemb;
    if (buf->len + total + 1 > buf->cap) {
        size_t new_cap = buf->cap == 0 ? 4096 : buf->cap * 2;
        while (buf->len + total + 1 > new_cap) {
            new_cap *= 2;
        }
        char *next = realloc(buf->data, new_cap);
        if (!next) {
            return 0;
        }
        buf->data = next;
        buf->cap = new_cap;
    }
    memcpy(buf->data + buf->len, ptr, total);
    buf->len += total;
    buf->data[buf->len] = '\0';
    return total;
}

int k9_http_post_json(const char *url, const char *body, const char *extra_hdr,
                      char *resp, size_t resp_cap, long *http_code) {
    CURL *curl = curl_easy_init();
    if (!curl) {
        return -1;
    }
    struct curl_buf buf = {0};
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    if (extra_hdr && extra_hdr[0]) {
        headers = curl_slist_append(headers, extra_hdr);
    }
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &buf);
    CURLcode rc = curl_easy_perform(curl);
    if (rc != CURLE_OK) {
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
        free(buf.data);
        return -2;
    }
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, http_code);
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    if (!buf.data) {
        return -3;
    }
    if (buf.len >= resp_cap) {
        free(buf.data);
        return -4;
    }
    memcpy(resp, buf.data, buf.len + 1);
    free(buf.data);
    return 0;
}

int k9_extract_json_string(const char *json, const char *key, char *out, size_t out_cap) {
    char pattern[128];
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    const char *pos = strstr(json, pattern);
    if (!pos) {
        return -1;
    }
    pos = strchr(pos, ':');
    if (!pos) {
        return -1;
    }
    pos++;
    while (*pos == ' ' || *pos == '\t') {
        pos++;
    }
    if (*pos != '"') {
        return -1;
    }
    pos++;
    size_t i = 0;
    while (*pos && *pos != '"' && i + 1 < out_cap) {
        out[i++] = *pos++;
    }
    out[i] = '\0';
    return i > 0 ? 0 : -1;
}

int k9_extract_error_code(const char *json, char *out, size_t out_cap) {
    const char *pos = strstr(json, "\"code\"");
    if (!pos) {
        return -1;
    }
    return k9_extract_json_string(pos, "code", out, out_cap);
}
