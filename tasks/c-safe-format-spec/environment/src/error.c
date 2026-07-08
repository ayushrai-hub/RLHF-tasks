#include "sfmt/error.h"
#include "sfmt/sfmt.h"

const char *sf_error_token(int code)
{
    switch (code) {
    case SF_ERR_NOT_IMPLEMENTED:
        return "@ERR:NOT_IMPLEMENTED";
    case SF_ERR_BAD_SPEC:
        return "@ERR:BAD_SPEC";
    case SF_ERR_MIX:
        return "@ERR:MIX";
    case SF_ERR_ARG_COUNT:
        return "@ERR:ARG_COUNT";
    case SF_ERR_ARG_TYPE:
        return "@ERR:ARG_TYPE";
    case SF_ERR_PERCENT_N:
        return "@ERR:PERCENT_N";
    case SF_ERR_BAD_UTF8:
        return "@ERR:BAD_UTF8";
    case SF_ERR_BAD_SCALAR:
        return "@ERR:BAD_SCALAR";
    case SF_ERR_NOMEM:
        return "@ERR:NOMEM";
    default:
        return 0;
    }
}
