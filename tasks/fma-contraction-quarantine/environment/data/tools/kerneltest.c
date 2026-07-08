/*
 * kerneltest is the library's command-line probe. It calls one kernel by name
 * with the double arguments that follow and prints the result as a C99 hex
 * float (%a), which round-trips the exact bits. Inputs are parsed with strtod,
 * so decimal, hex-float, and the tokens inf and nan all work.
 *
 *   kerneltest cross2 0.1 0.3 0.1 0.3
 *   kerneltest cascade 7 5 3
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "kernels.h"

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: kerneltest <kernel> [args...]\n");
        return 2;
    }
    const char *k = argv[1];
    double a[8] = {0};
    int n = argc - 2;
    for (int i = 0; i < n && i < 8; i++)
        a[i] = strtod(argv[2 + i], NULL);

    double r;
    if (!strcmp(k, "cross2"))            r = cross2(a[0], a[1], a[2], a[3]);
    else if (!strcmp(k, "clamp01"))      r = clamp01(a[0]);
    else if (!strcmp(k, "recover"))      r = recover(a[0], a[1]);
    else if (!strcmp(k, "sign_of"))      r = sign_of(a[0]);
    else if (!strcmp(k, "cascade"))      r = cascade(a[0], a[1], a[2]);
    else if (!strcmp(k, "roundtrip_residual")) r = roundtrip_residual(a[0]);
    else if (!strcmp(k, "polarity"))     r = polarity(a[0], a[1]);
    else if (!strcmp(k, "magdiff"))      r = magdiff(a[0], a[1]);
    else if (!strcmp(k, "domain_guard")) r = domain_guard(a[0], a[1]);
    else if (!strcmp(k, "horner"))       r = horner(a[0]);
    else {
        fprintf(stderr, "unknown kernel: %s\n", k);
        return 2;
    }
    printf("%a\n", r);
    return 0;
}
