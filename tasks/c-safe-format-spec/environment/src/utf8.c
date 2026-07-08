#include "sfmt/utf8.h"

int sf_utf8_scalar_valid(uint32_t cp)
{
    if (cp > 0x10FFFF)
        return 0;
    if (cp >= 0xD800 && cp <= 0xDFFF)
        return 0;
    return 1;
}

size_t sf_utf8_decode(const unsigned char *s, size_t len, uint32_t *cp)
{
    if (len == 0)
        return 0;
    unsigned char c = s[0];
    if (c < 0x80) {
        *cp = c;
        return 1;
    }
    if ((c & 0xE0) == 0xC0) {
        if (len < 2 || (s[1] & 0xC0) != 0x80)
            return 0;
        uint32_t v = ((uint32_t)(c & 0x1F) << 6) | (s[1] & 0x3F);
        if (v < 0x80)
            return 0;
        *cp = v;
        return 2;
    }
    if ((c & 0xF0) == 0xE0) {
        if (len < 3 || (s[1] & 0xC0) != 0x80 || (s[2] & 0xC0) != 0x80)
            return 0;
        uint32_t v = ((uint32_t)(c & 0x0F) << 12) |
                     ((uint32_t)(s[1] & 0x3F) << 6) | (s[2] & 0x3F);
        if (v < 0x800)
            return 0;
        if (v >= 0xD800 && v <= 0xDFFF)
            return 0;
        *cp = v;
        return 3;
    }
    if ((c & 0xF8) == 0xF0) {
        if (len < 4 || (s[1] & 0xC0) != 0x80 || (s[2] & 0xC0) != 0x80 ||
            (s[3] & 0xC0) != 0x80)
            return 0;
        uint32_t v = ((uint32_t)(c & 0x07) << 18) |
                     ((uint32_t)(s[1] & 0x3F) << 12) |
                     ((uint32_t)(s[2] & 0x3F) << 6) | (s[3] & 0x3F);
        if (v < 0x10000 || v > 0x10FFFF)
            return 0;
        *cp = v;
        return 4;
    }
    return 0;
}

size_t sf_utf8_encode(uint32_t cp, char out[4])
{
    if (!sf_utf8_scalar_valid(cp))
        return 0;
    if (cp < 0x80) {
        out[0] = (char)cp;
        return 1;
    }
    if (cp < 0x800) {
        out[0] = (char)(0xC0 | (cp >> 6));
        out[1] = (char)(0x80 | (cp & 0x3F));
        return 2;
    }
    if (cp < 0x10000) {
        out[0] = (char)(0xE0 | (cp >> 12));
        out[1] = (char)(0x80 | ((cp >> 6) & 0x3F));
        out[2] = (char)(0x80 | (cp & 0x3F));
        return 3;
    }
    out[0] = (char)(0xF0 | (cp >> 18));
    out[1] = (char)(0x80 | ((cp >> 12) & 0x3F));
    out[2] = (char)(0x80 | ((cp >> 6) & 0x3F));
    out[3] = (char)(0x80 | (cp & 0x3F));
    return 4;
}

long sf_utf8_count(const unsigned char *s, size_t len)
{
    size_t i = 0;
    long n = 0;
    while (i < len) {
        uint32_t cp;
        size_t step = sf_utf8_decode(s + i, len - i, &cp);
        if (step == 0)
            return -1;
        i += step;
        n++;
    }
    return n;
}
