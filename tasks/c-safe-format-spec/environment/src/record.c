#include "sfmt/record.h"

#include <stdio.h>

int sf_record_render(const sf_record *r, char *out, size_t cap)
{
    int off = snprintf(out, cap, "[%s] ", sf_level_name(r->level));
    if (off < 0 || (size_t)off >= cap)
        return SF_ERR_NOMEM;
    int rc = sf_format(r->fmt, r->args, r->nargs, out + off, cap - (size_t)off);
    if (rc < 0)
        return rc;
    return off + rc;
}
