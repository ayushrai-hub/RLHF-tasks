#include <stdio.h>
#include <stdint.h>
#include <math.h>
#include "grid_pll.h"

// --- Hardware & System Constants ---
#define SAMPLES_PER_CYCLE 2048
#define NOMINAL_FREQ_HZ 60.0

// --- Test Evaluation Parameters ---
#define TARGET_FREQ_TOLERANCE 0.005
#define REQUIRED_CONSECUTIVE_LOCKS 10

// A properly tuned loop (fn=0.38, zeta=1.06) settles a large 1.8Hz step 
// in ~250-300 frames. We cap it at 350 frames to fail naive averaging filters.
#define MAX_FRAMES_TO_LOCK 350

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Test across the operating range mandated by the instructions
const double TEST_FREQUENCIES[] = {58.2, 61.8, 60.05};
const int NUM_TESTS = 3;

int main() {
    uint16_t frame[SAMPLES_PER_CYCLE];
    
    for (int t = 0; t < NUM_TESTS; t++) {
        double target_freq = TEST_FREQUENCIES[t];
        printf("\n--- Testing Target Frequency: %.2f Hz ---\n", target_freq);
        
        // Re-initialize the agent's PLL state for each test
        grid_pll_init();
        
        double grid_phase = 0.0;
        double reported_f = NOMINAL_FREQ_HZ;
        double current_sampling_f = reported_f * SAMPLES_PER_CYCLE;
        int consecutive_locked_frames = 0;
        int lock_achieved = 0;

        for (int f = 0; f < MAX_FRAMES_TO_LOCK; f++) {
            double dt = 1.0 / current_sampling_f; 
            
            for (int i = 0; i < SAMPLES_PER_CYCLE; i++) {
                grid_phase += 2.0 * M_PI * target_freq * dt;
                if (grid_phase > 2.0 * M_PI) grid_phase -= 2.0 * M_PI;
                frame[i] = (uint16_t)(2048.0 + 2047.0 * sin(grid_phase));
            }
            
            reported_f = grid_pll_update(frame);
            current_sampling_f = reported_f * SAMPLES_PER_CYCLE;

            if (reported_f > (target_freq - TARGET_FREQ_TOLERANCE) && 
                reported_f < (target_freq + TARGET_FREQ_TOLERANCE)) {
                
                consecutive_locked_frames++;
                
                if (consecutive_locked_frames >= REQUIRED_CONSECUTIVE_LOCKS) {
                    printf("PASS: PLL achieved stable lock at frame %d (Frequency: %f Hz)\n", f, reported_f);
                    lock_achieved = 1;
                    break; 
                }
            } else {
                consecutive_locked_frames = 0; 
            }
        }

        if (!lock_achieved) {
            printf("FAIL: Expected %.2f Hz, but PLL failed to stabilize in time. Final reported: %f Hz\n", 
                   target_freq, reported_f);
            return 1;
        }
    }
    
    printf("\nALL PLL TESTS PASSED\n");
    return 0;
}