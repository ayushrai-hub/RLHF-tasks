#ifndef GRID_PLL_H
#define GRID_PLL_H

#include <stdint.h>

void grid_pll_init(void);

double grid_pll_update(const uint16_t *adc_data);

#endif