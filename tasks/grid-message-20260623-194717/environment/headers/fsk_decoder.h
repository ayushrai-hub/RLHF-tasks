#ifndef FSK_DECODER_H
#define FSK_DECODER_H

#include <stdint.h>
#include <stdbool.h>

/**
 * @brief Initialize the FSK demodulator and UART framer state.
 */
void fsk_decoder_init(void);

/**
 * @brief Process a newly tracked instantaneous frequency.
 * * @param current_freq The current tracked frequency from the PLL.
 * @param decoded_char Pointer to store the successfully decoded ASCII character.
 * @return 1 if a new character was decoded in this frame, 0 otherwise.
 */
int fsk_decoder_process_freq(double current_freq, char *decoded_char);

#endif // FSK_DECODER_H