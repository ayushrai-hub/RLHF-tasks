#include "adc_buf.h"
#include <math.h>
#include <stdint.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// --- Basic Simulation State ---
static double current_sampling_freq = 122880.0; // Nominal 60Hz * 2048
static double current_phase = 0.0;

// --- Hardware Abstraction API ---

void set_adc_sampling_frequency(double target_hz) {
    // you do not need to implement this. The mock_adc.c will be supplied by the test harness.
    // you will not need to call this in milestones 1 and 2.
}

void fill_adc_buf(adc_buf_t *buf) {
    // you will use this function to get the sampling frame.
    // you do not implement this function.
}