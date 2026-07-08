#include "sfmt/hexdump.h"

#include "sfmt/args.h"
#include "sfmt/sfmt.h"
#include "sfmt/writer.h"

int sf_hexdump(const unsigned char *data, size_t n, char *out, size_t cap)
{
    sf_writer w;
    sf_writer_init(&w, out, cap);
    char line[16];

    for (size_t off = 0; off < n; off += 16) {
        sf_arg a = sf_u64(off);
        int r = sf_format("%08x", &a, 1, line, sizeof(line));
        if (r < 0)
            return r;
        sf_writer_write(&w, line, (size_t)r);
        sf_writer_write(&w, "  ", 2);

        for (size_t k = 0; k < 16; k++) {
            if (off + k < n) {
                sf_arg b = sf_u64(data[off + k]);
                int rr = sf_format("%02x", &b, 1, line, sizeof(line));
                if (rr < 0)
                    return rr;
                sf_writer_write(&w, line, (size_t)rr);
            } else {
                sf_writer_write(&w, "  ", 2);
            }
            sf_writer_put(&w, ' ');
        }

        sf_writer_write(&w, "|", 1);
        for (size_t k = 0; k < 16 && off + k < n; k++) {
            unsigned char c = data[off + k];
            sf_writer_put(&w, (c >= 0x20 && c < 0x7F) ? (char)c : '.');
        }
        sf_writer_write(&w, "|\n", 2);
    }

    if (w.overflow)
        return SF_ERR_NOMEM;
    return (int)w.len;
}
