#include "current_math.h"
#include <math.h>

int glassreef_drift_penalty(double mean_mps, double bearing_deg, int depth_m) {
    double radians = bearing_deg * 3.14159265358979323846 / 180.0;
    double directional = fabs(sin(radians)) * 5.0;
    double depth_component = depth_m > 3000 ? (depth_m - 3000) / 900.0 : 0.0;
    double raw = mean_mps * 30.0 + directional + depth_component;
    return (int) floor(raw + 0.5);
}
