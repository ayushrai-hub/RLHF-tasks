#include "t8.h"
#include <stdio.h>

void actuator_diag(const ActuatorBatch *batch) {
    if (batch == NULL) {
        return;
    }
    printf("batch count=%d pending=%llu\n", batch->count, (unsigned long long)batch->pending_epoch);
}
