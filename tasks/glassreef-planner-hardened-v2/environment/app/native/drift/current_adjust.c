#include "current_math.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: current_adjust mean_mps bearing_deg depth_m\n");
        return 2;
    }
    double mean = atof(argv[1]);
    double bearing = atof(argv[2]);
    int depth = atoi(argv[3]);
    printf("%d\n", glassreef_drift_penalty(mean, bearing, depth));
    return 0;
}
