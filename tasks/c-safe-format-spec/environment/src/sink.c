#include "sfmt/sink.h"

void sf_sink_init_file(sf_sink *s, FILE *fp)
{
    s->fp = fp;
}

int sf_sink_emit(sf_sink *s, const char *bytes, size_t n)
{
    return fwrite(bytes, 1, n, s->fp) == n ? 0 : -1;
}
