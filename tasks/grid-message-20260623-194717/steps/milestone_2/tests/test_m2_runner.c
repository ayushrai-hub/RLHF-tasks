#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
#include "fsk_decoder.h" 

int main(void) {
    srand(42);
    
    double carriers[] = {58.0, 59.3, 60.0, 61.2, 62.0};
    // Test a different arbitrary string for each carrier frequency
    const char *test_messages[] = {"Hola!!!!", "ZEPHYR", "FSK_test", "12345", "Data"};
    
    int num_trials = sizeof(carriers) / sizeof(carriers[0]);
    int successful_trials = 0;

    for (int t = 0; t < num_trials; t++) {
        double base_carrier = carriers[t];
        double mark_freq = base_carrier + 0.05;
        double space_freq = base_carrier - 0.05;
        
        const char *current_message = test_messages[t];
        int msg_len = strlen(current_message);
        
        // CRITICAL: Reset the decoder's state machine and moving averages
        // so it treats this trial as a brand new boot sequence!
        fsk_decoder_init(); 
        
        char decoded = '\0';
        int char_index = 0;
        char output_buffer[64] = {0};

        // Variable Preamble
        int preamble_frames = 180 + (rand() % 61);
        for (int i = 0; i < preamble_frames; i++) {
            fsk_decoder_process_freq(mark_freq, &decoded);
        }

        // Transmit the message bytes
        for (int i = 0; i < msg_len; i++) {
            char current_char = current_message[i];

            int drifted_periods[10];
            for (int b = 0; b < 10; b++) {
                drifted_periods[b] = 58 + (rand() % 5);
            }

            for (int bit_idx = 0; bit_idx < 10; bit_idx++) {
                int bit_val;
                if (bit_idx == 0) bit_val = 0; 
                else if (bit_idx == 9) bit_val = 1; 
                else bit_val = (current_char >> (bit_idx - 1)) & 0x01;

                double freq_to_send = bit_val ? mark_freq : space_freq;
                int frames_for_this_bit = drifted_periods[bit_idx];

                for (int f = 0; f < frames_for_this_bit; f++) {
                    if (fsk_decoder_process_freq(freq_to_send, &decoded)) {
                        if (decoded >= 32 && decoded <= 126) {
                            output_buffer[char_index++] = decoded;
                        }
                    }
                }
            }
        }
        
        output_buffer[char_index] = '\0';
        
        // Evaluate the output internally instead of printing it
        if (strcmp(output_buffer, current_message) == 0) {
            successful_trials++;
        } else {
            // Print error ONLY if it fails, so Python logs why it failed
            printf("FAIL: Trial %d (%.1f Hz). Expected '%s', Got '%s'\n", 
                   t, base_carrier, current_message, output_buffer);
        }
    }

    // STRICT VALIDATION: Print EXACTLY "PASS" for the Python grader
    if (successful_trials == num_trials) {
        printf("PASS\n");
    }

    return 0;
}