#include "sfmt/field.h"

#include "sfmt/args.h"

#include <string.h>

int sf_field_render(const sf_field *f, char *out, size_t cap)
{
    sf_arg args[2];
    args[0] = sf_str(f->key, strlen(f->key));
    args[1] = f->val;

    const char *fmt;
    switch (f->val.type) {
    case SF_ARG_I64:
        fmt = "%s=%d";
        break;
    case SF_ARG_U64:
        fmt = "%s=%u";
        break;
    case SF_ARG_STR:
        fmt = "%s=%s";
        break;
    case SF_ARG_BYTE:
        fmt = "%s=%c";
        break;
    case SF_ARG_SCALAR:
        fmt = "%s=%C";
        break;
    default:
        return SF_ERR_ARG_TYPE;
    }
    return sf_format(fmt, args, 2, out, cap);
}
