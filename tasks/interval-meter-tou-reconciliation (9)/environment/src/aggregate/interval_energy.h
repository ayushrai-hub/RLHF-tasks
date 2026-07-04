#ifndef TOU_INTERVAL_ENERGY_H
#define TOU_INTERVAL_ENERGY_H

double interval_kwh_delta(double prev_register, double curr_register, double register_max, int *rollover_out);

#endif
