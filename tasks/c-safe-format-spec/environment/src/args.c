#include "sfmt/args.h"

sf_arg sf_i64(int64_t v)
{
    sf_arg a;
    a.type = SF_ARG_I64;
    a.i64 = v;
    a.u64 = 0;
    a.str = 0;
    a.slen = 0;
    return a;
}

sf_arg sf_u64(uint64_t v)
{
    sf_arg a;
    a.type = SF_ARG_U64;
    a.i64 = 0;
    a.u64 = v;
    a.str = 0;
    a.slen = 0;
    return a;
}

sf_arg sf_str(const char *s, size_t n)
{
    sf_arg a;
    a.type = SF_ARG_STR;
    a.i64 = 0;
    a.u64 = 0;
    a.str = s;
    a.slen = n;
    return a;
}

sf_arg sf_byte(unsigned v)
{
    sf_arg a;
    a.type = SF_ARG_BYTE;
    a.i64 = 0;
    a.u64 = v & 0xFF;
    a.str = 0;
    a.slen = 0;
    return a;
}

sf_arg sf_scalar(uint32_t v)
{
    sf_arg a;
    a.type = SF_ARG_SCALAR;
    a.i64 = 0;
    a.u64 = v;
    a.str = 0;
    a.slen = 0;
    return a;
}
