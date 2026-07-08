#include <math.h>
#include <stdio.h>
#include <stdlib.h>

extern double glassreef_duration_hint(double length_nm);

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: repair_duration length_nm\n");
        return 2;
    }
    double length = atof(argv[1]);
    int hours = (int) ceil(glassreef_duration_hint(length));
    if (hours < 1) {
        hours = 1;
    }
    printf("%d\n", hours);
    return 0;
}
