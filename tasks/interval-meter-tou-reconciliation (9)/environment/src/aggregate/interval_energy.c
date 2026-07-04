#include "aggregate/interval_energy.h"

double interval_kwh_delta(double prev_register, double curr_register, double register_max, int *rollover_out) {
    (void)register_max;
    double delta = curr_register - prev_register;
    if (delta < 0.0) {
        if (rollover_out) {
            (*rollover_out) += 1;
        }
    }
    return delta;
}
