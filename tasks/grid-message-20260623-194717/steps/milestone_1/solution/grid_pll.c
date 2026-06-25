#include "grid_pll.h"
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static double integral = 0.0;

void grid_pll_init(void) {
    integral = 0.0;
}

double grid_pll_update(const uint16_t *adc_data) {
    double i_sum = 0.0;
    double q_sum = 0.0;

    // 1. Orthogonal Mixing to extract Phase Error
    for (int i = 0; i < 2048; i++) {
        double voltage = (double)adc_data[i] - 2048.0;
        double local_phase = (2.0 * M_PI * i) / 2048.0;
        
        i_sum += voltage * cos(local_phase);
        q_sum += voltage * sin(local_phase);
    }
    
    // Calculate phase error in radians
    // CRITICAL FIX: atan2(y, x). i_sum is opposite (sine), q_sum is adjacent (cosine).
    double phase_error = atan2(i_sum, q_sum);

    // 2. PI Controller Math (fn = 0.38 Hz, zeta = 1.06)
    double kp = 0.8056;
    double ki = 0.01512;

    integral += phase_error;
    
    // Calculate tracked instantaneous line frequency
    double f_line = 60.0 + (kp * phase_error) + (ki * integral);

    return f_line;
}