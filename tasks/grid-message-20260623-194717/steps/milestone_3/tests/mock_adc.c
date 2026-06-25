#include "adc_buf.h"
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <zephyr/kernel.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// --- SECURE WORD SELECTION ---
#ifdef TEST_SECRET_WORD
// Synchronize with the Python Test Wrapper macro injection
#define XSTR(x) STR(x)
#define STR(x) #x
static const char *secret_word = XSTR(TEST_SECRET_WORD);
#else
// Fallback for local manual testing
static const char *secret_word = "ORACLE"; 
#endif

static double true_base_freq = 0.0;
static double true_bit_period = 0.0;
static double current_sampling_freq = 122880.0;
static double global_time = 0.0;
static double current_phase = 0.0;
static int initialized = 0;
static const double DEVIATION = 0.05;

void set_adc_sampling_frequency(double target_hz) {
    current_sampling_freq = target_hz;
}

static int symbol_from_uart_byte(char c, int bit_index) {
    if (bit_index == 0) return 0; // Start bit
    if (bit_index >= 1 && bit_index <= 8) {
        return (c >> (bit_index - 1)) & 0x01;
    }
    return 1; // Stop bit
}

void fill_adc_buf(adc_buf_t *buf) {
    if (!initialized) {
        srand(42);
        // Randomize carrier and baud rate drift as per specs
        true_base_freq = 58.0 + ((double)rand() / RAND_MAX) * 4.0;
        true_bit_period = 0.98 + ((double)rand() / RAND_MAX) * 0.04;
        
        // DELETED the printf that leaked the secret_word to prevent agent cheating!
        printf("[MOCK_ENV] CARRIER_FREQ: %.3f Hz\n", true_base_freq);
        printf("[MOCK_ENV] BIT_PERIOD: %.3f s\n", true_bit_period);
        initialized = 1;
    }

    uint16_t *buffer = buf->adc_buf;
    int msg_len = (int)strlen(secret_word) + 1; // +1 to include the null terminator
    // Check if Python ordered us to run the empty test
    char *scenario = getenv("SCENARIO");
    if (scenario != NULL && strcmp(scenario, "empty") == 0) {
        msg_len = 0; // Transmit nothing!
    }
    double start_s = 5.0; // 5 seconds of preamble
    double total_time = 10.0 * msg_len * true_bit_period;

    for (size_t i = 0; i < SAMPLES_PER_CYCLE; i++) {
        double dt = 1.0 / current_sampling_freq;
        global_time += dt;

        double current_freq = true_base_freq;

        if (global_time >= start_s && global_time < start_s + total_time) {
            double msg_time = global_time - start_s;
            int total_bits = (int)(msg_time / true_bit_period);
            int char_index = total_bits / 10;
            int bit_index = total_bits % 10;

            char c = '\0';
            if (char_index < msg_len) {
                c = secret_word[char_index];
            }

            int bit_val = symbol_from_uart_byte(c, bit_index);
            current_freq += (bit_val == 1) ? DEVIATION : -DEVIATION;
        } else {
            // Preamble or Post-Transmission (Idle Mark)
            current_freq += DEVIATION;
        }

        current_phase += 2.0 * M_PI * current_freq * dt;
        if (current_phase > 2.0 * M_PI) {
            current_phase -= 2.0 * M_PI;
        }

        buffer[i] = (uint16_t)(2047.0 * sin(current_phase) + 2048.0);
    }
}