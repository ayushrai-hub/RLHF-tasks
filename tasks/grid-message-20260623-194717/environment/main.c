#include "adc_buf.h"
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <zephyr/device.h>
#include <zephyr/kernel.h>
#include "grid_pll.h"
#include "fsk_decoder.h"

#define SAMPLES_PER_CYCLE 2048
#define NOMINAL_LINE_FREQUENCY 60.0
#define NUMBER_OF_ADC_FRAMES 12000

int main(void) {
    // TODO: Initialize your modules

    char decoded_message[100] = {0};
    int message_index = 0;
    int frames_processed = 0;

    // Start with nominal frequency
    double current_f_line = NOMINAL_LINE_FREQUENCY;

    for (int i = 0; i < NUMBER_OF_ADC_FRAMES; ++i) {

        // TODO update current_f_line
        // TODO decode the message to decoded_message[]

        frames_processed++;
    }

    // TODO print out decoded message or no message found strings

    return 0;
}