#include "specparse.h"

#include <stdlib.h>

/*
 * TODO(milestone 3): implement the .spec parser described in docs/FORMAT.md.
 * The stub fails to parse anything so statctl reports no tests until done.
 */

int sk_parse_spec(const char *path, sk_suite *suite)
{
    (void)path;
    suite->tests = NULL;
    suite->count = 0;
    return 1; /* not implemented */
}

void sk_suite_free(sk_suite *suite)
{
    free(suite->tests);
    suite->tests = NULL;
    suite->count = 0;
}
