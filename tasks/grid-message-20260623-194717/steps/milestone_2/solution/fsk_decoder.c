#include "fsk_decoder.h"

// State Machine: 0=CALIBRATING, 1=IDLE, 2=DECODING
static int state = 0;
static double calib_sum = 0.0;
static int calib_count = 0;
static double threshold = 0.0;

static int bit_timer = 0;
static char current_char = 0;

void fsk_decoder_init(void)
{
    state = 0;
    calib_sum = 0.0;
    calib_count = 0;
}

int fsk_decoder_process_freq(double current_freq, char *decoded_char)
{
    // 1. Calibration Phase (Average the preamble Mark signal)
    if (state == 0)
    {
        calib_sum += current_freq;
        calib_count++;
        // Wait 2 seconds (120 frames) to get a stable average
        if (calib_count == 120)
        {
            double mark_freq = calib_sum / 120.0;
            threshold = mark_freq - 0.05; // Space is 0.1Hz below Mark
            state = 1;
        }
        return 0;
    }

    // 2. Idle Phase (Wait for Start Bit)
    if (state == 1)
    {
        if (current_freq < threshold)
        {
            state = 2; // Transitioned to Space (Start Bit)
            bit_timer = 0;
            current_char = 0;
        }
        return 0;
    }

    // 3. Decoding Phase (Slice 8N1 Frame)
    if (state == 2)
    {
        bit_timer++;

        // --- NEW: FALSE START REJECTION ---
        // Verify the start bit is still physically present at its midpoint.
        // If it isn't, it was just PLL ripple/noise. Reset back to Idle!
        if (bit_timer == 30)
        {
            if (current_freq >= threshold)
            {
                state = 1;
                return 0;
            }
        }

        // Sample exactly in the middle of each 60-frame bit period
        if (bit_timer >= 60 && bit_timer < 540)
        {
            if ((bit_timer % 60) == 30)
            {
                int bit_index = (bit_timer - 60) / 60;
                int bit_val = (current_freq > threshold) ? 1 : 0;
                current_char |= (bit_val << bit_index);
            }
        }

        // Stop bit arrives at 540-600. Return character at midpoint.
        if (bit_timer == 570)
        {
            *decoded_char = current_char;
            state = 1;
            return 1;
        }
    }
    return 0;
}