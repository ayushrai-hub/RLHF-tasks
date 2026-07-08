#include "sfmt/sfmt.h"
#include "sfmt/utf8.h"
#include "sfmt/writer.h"

#include <string.h>

#define SF_MAXRUN 4
#define SF_PAD_MAX 4096
#define SF_BODY_CAP 16384

static int read_run(const char *f, size_t i, size_t n, int *val, size_t *rl)
{
    size_t start = i;
    long v = 0;
    while (i < n && f[i] >= '0' && f[i] <= '9') {
        v = v * 10 + (f[i] - '0');
        i++;
    }
    *rl = i - start;
    *val = (int)v;
    return (int)i;
}

static int utoa(uint64_t v, int base, int upper, char *out)
{
    const char *L = upper ? "0123456789ABCDEF" : "0123456789abcdef";
    char tmp[72];
    int t = 0;
    if (v == 0) {
        out[0] = '0';
        return 1;
    }
    while (v) {
        tmp[t++] = L[v % (uint64_t)base];
        v /= (uint64_t)base;
    }
    for (int k = 0; k < t; k++)
        out[k] = tmp[t - 1 - k];
    return t;
}

static int group_from_right(const char *sig, int L, char *out)
{
    int oi = 0;
    for (int i = 0; i < L; i++) {
        if (i > 0 && (L - i) % 3 == 0)
            out[oi++] = '_';
        out[oi++] = sig[i];
    }
    return oi;
}

static int grouped_zero_fill(const char *sig, int siglen, int F, char *out)
{
    int n = siglen > 0 ? siglen : 1;
    while (n + (n - 1) / 3 < F)
        n++;
    char digits[SF_BODY_CAP];
    int pad = n - siglen;
    for (int k = 0; k < pad; k++)
        digits[k] = '0';
    memcpy(digits + pad, sig, (size_t)siglen);
    char g[SF_BODY_CAP];
    int glen = group_from_right(digits, n, g);
    if (glen > F) {
        int off = glen - F;
        memcpy(out, g + off, (size_t)F);
        if (F > 0 && out[0] == '_')
            out[0] = '0';
        return F;
    }
    memcpy(out, g, (size_t)glen);
    return glen;
}

static void emit_numeric(sf_writer *w, char conv, const sf_arg *a, int f_minus,
                         int f_plus, int f_space, int f_hash, int f_zero,
                         int f_group, int width, int precision)
{
    char sig[80];
    int siglen;
    int is_dec = (conv == 'd' || conv == 'i' || conv == 'u');
    int value_is_zero;
    char sign = 0;

    if (conv == 'd' || conv == 'i') {
        int64_t v = a->i64;
        int neg = v < 0;
        uint64_t m = neg ? (~(uint64_t)v + 1u) : (uint64_t)v;
        value_is_zero = (v == 0);
        siglen = utoa(m, 10, 0, sig);
        if (neg)
            sign = '-';
        else if (f_plus)
            sign = '+';
        else if (f_space)
            sign = ' ';
    } else {
        uint64_t val = a->u64;
        value_is_zero = (val == 0);
        int base = (conv == 'u') ? 10 : (conv == 'x' || conv == 'X') ? 16
                   : (conv == 'o')                                   ? 8
                                                                     : 2;
        siglen = utoa(val, base, (conv == 'X'), sig);
    }

    char pd[SF_BODY_CAP];
    int pdlen = 0;
    if (precision >= 0 && precision == 0 && value_is_zero) {
        pdlen = 0;
    } else {
        int pad = (precision >= 0 && siglen < precision) ? precision - siglen : 0;
        for (int k = 0; k < pad; k++)
            pd[pdlen++] = '0';
        memcpy(pd + pdlen, sig, (size_t)siglen);
        pdlen += siglen;
    }

    int grouped = is_dec && f_group;

    char prefix[2];
    int prlen = 0;
    if (conv == 'd' || conv == 'i') {
        if (sign)
            prefix[prlen++] = sign;
    } else if (f_hash && !value_is_zero) {
        if (conv == 'x') {
            prefix[0] = '0';
            prefix[1] = 'x';
            prlen = 2;
        } else if (conv == 'X') {
            prefix[0] = '0';
            prefix[1] = 'X';
            prlen = 2;
        } else if (conv == 'o') {
            prefix[0] = '0';
            prefix[1] = 'o';
            prlen = 2;
        } else if (conv == 'b') {
            prefix[0] = '0';
            prefix[1] = 'b';
            prlen = 2;
        }
    }

    int zero = f_zero && !f_minus && precision < 0;

    char gb[SF_BODY_CAP];
    int gblen;
    if (grouped)
        gblen = group_from_right(pd, pdlen, gb);
    else {
        memcpy(gb, pd, (size_t)pdlen);
        gblen = pdlen;
    }
    int natural = prlen + gblen;

    if (width > natural && zero) {
        int F = width - prlen;
        char body[SF_BODY_CAP];
        int blen;
        if (grouped) {
            blen = grouped_zero_fill(pd, pdlen, F, body);
        } else {
            blen = 0;
            for (int k = 0; k < F - pdlen; k++)
                body[blen++] = '0';
            memcpy(body + blen, pd, (size_t)pdlen);
            blen += pdlen;
        }
        sf_writer_write(w, prefix, (size_t)prlen);
        sf_writer_write(w, body, (size_t)blen);
        return;
    }

    if (width > natural) {
        int pad = width - natural;
        if (f_minus) {
            sf_writer_write(w, prefix, (size_t)prlen);
            sf_writer_write(w, gb, (size_t)gblen);
            sf_writer_fill(w, ' ', (size_t)pad);
        } else {
            sf_writer_fill(w, ' ', (size_t)pad);
            sf_writer_write(w, prefix, (size_t)prlen);
            sf_writer_write(w, gb, (size_t)gblen);
        }
    } else {
        sf_writer_write(w, prefix, (size_t)prlen);
        sf_writer_write(w, gb, (size_t)gblen);
    }
}

static void emit_bytes(sf_writer *w, const char *p, size_t nn, int f_minus,
                       int width)
{
    if (width > 0 && (size_t)width > nn) {
        size_t pad = (size_t)width - nn;
        if (f_minus) {
            sf_writer_write(w, p, nn);
            sf_writer_fill(w, ' ', pad);
        } else {
            sf_writer_fill(w, ' ', pad);
            sf_writer_write(w, p, nn);
        }
    } else {
        sf_writer_write(w, p, nn);
    }
}

int sf_format(const char *fmt, const sf_arg *args, size_t nargs, char *out,
              size_t outcap)
{
    sf_writer w;
    sf_writer_init(&w, out, outcap);

    size_t n = 0;
    while (fmt[n] != 0)
        n++;

    int mode = 0;
    size_t cursor = 0;
    uint64_t referenced = 0;
    size_t i = 0;

    while (i < n) {
        unsigned char b = (unsigned char)fmt[i];
        if (b != '%') {
            sf_writer_put(&w, (char)b);
            i++;
            continue;
        }
        i++;
        if (i >= n)
            return SF_ERR_BAD_SPEC;

        int index = -1;
        {
            int v;
            size_t rl;
            size_t j = (size_t)read_run(fmt, i, n, &v, &rl);
            if (rl > 0 && j < n && fmt[j] == '$') {
                if (rl > SF_MAXRUN)
                    return SF_ERR_BAD_SPEC;
                index = v;
                i = j + 1;
            }
        }

        int f_minus = 0, f_plus = 0, f_space = 0, f_hash = 0, f_zero = 0,
            f_group = 0;
        while (i < n) {
            char c = fmt[i];
            if (c == '-')
                f_minus = 1;
            else if (c == '+')
                f_plus = 1;
            else if (c == ' ')
                f_space = 1;
            else if (c == '#')
                f_hash = 1;
            else if (c == '0')
                f_zero = 1;
            else if (c == '\'')
                f_group = 1;
            else
                break;
            i++;
        }

        int width = -1;
        int width_star = 0;
        if (i < n && fmt[i] == '*') {
            width_star = 1;
            i++;
        } else {
            int v;
            size_t rl;
            i = (size_t)read_run(fmt, i, n, &v, &rl);
            if (rl > SF_MAXRUN)
                return SF_ERR_BAD_SPEC;
            if (rl > 0)
                width = v;
        }

        int precision = -1;
        int prec_star = 0;
        if (i < n && fmt[i] == '.') {
            i++;
            if (i < n && fmt[i] == '*') {
                prec_star = 1;
                i++;
            } else {
                int v;
                size_t rl;
                i = (size_t)read_run(fmt, i, n, &v, &rl);
                if (rl > SF_MAXRUN)
                    return SF_ERR_BAD_SPEC;
                precision = (rl > 0) ? v : 0;
            }
        }

        if (i >= n)
            return SF_ERR_BAD_SPEC;
        char conv = fmt[i];
        i++;

        if (conv == '%') {
            if (index != -1 || f_minus || f_plus || f_space || f_hash ||
                f_zero || f_group || width != -1 || width_star ||
                precision != -1 || prec_star)
                return SF_ERR_BAD_SPEC;
            sf_writer_put(&w, '%');
            continue;
        }
        if (!strchr("diuxXobcCsn", conv))
            return SF_ERR_BAD_SPEC;
        if (conv == 'n')
            return SF_ERR_PERCENT_N;

        if ((width_star || prec_star) && index != -1)
            return SF_ERR_BAD_SPEC;

        if (index != -1) {
            if (mode == 1)
                return SF_ERR_MIX;
            mode = 2;
        } else {
            if (mode == 2)
                return SF_ERR_MIX;
            mode = 1;
        }

        int eff_minus = f_minus;
        if (width_star) {
            if (cursor >= nargs)
                return SF_ERR_ARG_COUNT;
            const sf_arg *wa = &args[cursor++];
            if (wa->type != SF_ARG_I64)
                return SF_ERR_ARG_TYPE;
            int64_t wv = wa->i64;
            if (wv < 0) {
                eff_minus = 1;
                if (-wv > SF_PAD_MAX)
                    return SF_ERR_BAD_SPEC;
                width = (int)(-wv);
            } else {
                if (wv > SF_PAD_MAX)
                    return SF_ERR_BAD_SPEC;
                width = (int)wv;
            }
        }
        if (prec_star) {
            if (cursor >= nargs)
                return SF_ERR_ARG_COUNT;
            const sf_arg *pa = &args[cursor++];
            if (pa->type != SF_ARG_I64)
                return SF_ERR_ARG_TYPE;
            int64_t pv = pa->i64;
            if (pv < 0)
                precision = -1;
            else {
                if (pv > SF_PAD_MAX)
                    return SF_ERR_BAD_SPEC;
                precision = (int)pv;
            }
        }

        const sf_arg *a;
        if (index != -1) {
            if (index < 1 || (size_t)index > nargs)
                return SF_ERR_ARG_COUNT;
            referenced |= (uint64_t)1 << (index - 1);
            a = &args[index - 1];
        } else {
            if (cursor >= nargs)
                return SF_ERR_ARG_COUNT;
            a = &args[cursor++];
        }

        sf_argtype need;
        switch (conv) {
        case 'd':
        case 'i':
            need = SF_ARG_I64;
            break;
        case 'u':
        case 'x':
        case 'X':
        case 'o':
        case 'b':
            need = SF_ARG_U64;
            break;
        case 'c':
            need = SF_ARG_BYTE;
            break;
        case 'C':
            need = SF_ARG_SCALAR;
            break;
        default:
            need = SF_ARG_STR;
            break;
        }
        if (a->type != need)
            return SF_ERR_ARG_TYPE;

        if (strchr("diuxXob", conv)) {
            emit_numeric(&w, conv, a, eff_minus, f_plus, f_space, f_hash, f_zero,
                         f_group, width, precision);
        } else if (conv == 'c') {
            char cb = (char)(a->u64 & 0xFF);
            emit_bytes(&w, &cb, 1, eff_minus, width);
        } else if (conv == 'C') {
            if (!sf_utf8_scalar_valid((uint32_t)a->u64))
                return SF_ERR_BAD_SCALAR;
            char buf[4];
            size_t enc = sf_utf8_encode((uint32_t)a->u64, buf);
            emit_bytes(&w, buf, enc, eff_minus, width);
        } else {
            const char *raw = a->str;
            size_t rawlen = a->slen;
            if (precision < 0) {
                emit_bytes(&w, raw, rawlen, eff_minus, width);
            } else {
                long cnt = sf_utf8_count((const unsigned char *)raw, rawlen);
                if (cnt < 0)
                    return SF_ERR_BAD_UTF8;
                size_t take = rawlen;
                if (cnt > precision) {
                    size_t pos = 0;
                    int kept = 0;
                    while (kept < precision) {
                        uint32_t cp;
                        pos += sf_utf8_decode((const unsigned char *)raw + pos,
                                              rawlen - pos, &cp);
                        kept++;
                    }
                    take = pos;
                }
                emit_bytes(&w, raw, take, eff_minus, width);
            }
        }
    }

    if (mode == 2) {
        for (size_t k = 0; k < nargs; k++)
            if (!(referenced & ((uint64_t)1 << k)))
                return SF_ERR_ARG_COUNT;
    } else {
        if (cursor != nargs)
            return SF_ERR_ARG_COUNT;
    }

    if (w.overflow)
        return SF_ERR_NOMEM;
    return (int)w.len;
}
