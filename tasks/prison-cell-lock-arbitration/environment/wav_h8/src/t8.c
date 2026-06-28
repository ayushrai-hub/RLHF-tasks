#include "t8.h"
#include <string.h>

static int flush_batch(ActuatorBatch *batch, uint64_t epoch) {
    for (int i = 0; i < batch->count; i++) {
        batch->cells[i].epoch = epoch;
    }
    batch->last_commit_epoch = epoch;
    batch->count = 0;
    return 0;
}

void batch_reset(ActuatorBatch *batch) {
    memset(batch, 0, sizeof(*batch));
}

void batch_queue(ActuatorBatch *batch, const char *cell_id, uint64_t epoch) {
    if (batch->count >= ACT_MAX_CELLS) {
        return;
    }
    ActuatorCell *slot = &batch->cells[batch->count++];
    strncpy(slot->cell_id, cell_id, sizeof(slot->cell_id) - 1);
    slot->epoch = epoch;
    batch->pending_epoch = epoch;
}

int flush_t8(ActuatorBatch *batch, uint64_t commit_epoch) {
    (void)commit_epoch;
    return flush_batch(batch, batch->pending_epoch);
}

uint64_t batch_last_commit_epoch(const ActuatorBatch *batch) {
    return batch->last_commit_epoch;
}
