#include "sfmt/logger.h"

void sf_logger_init(sf_logger *lg, sf_sink sink, sf_level min)
{
    lg->sink = sink;
    lg->min = min;
}

int sf_logger_emit(sf_logger *lg, const sf_record *r)
{
    if (r->level < lg->min)
        return 0;
    char buf[65536];
    int rc = sf_record_render(r, buf, sizeof(buf));
    if (rc < 0)
        return rc;
    if (sf_sink_emit(&lg->sink, buf, (size_t)rc) != 0)
        return -1;
    sf_sink_emit(&lg->sink, "\n", 1);
    return rc;
}
