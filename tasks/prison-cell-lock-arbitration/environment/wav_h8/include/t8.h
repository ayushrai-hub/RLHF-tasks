#ifndef ACTUATOR_BATCH_H
#define ACTUATOR_BATCH_H

#include <stdint.h>

#define ACT_MAX_CELLS 32

typedef struct {
    char cell_id[16];
    uint64_t epoch;
} ActuatorCell;

typedef struct {
    ActuatorCell cells[ACT_MAX_CELLS];
    int count;
    uint64_t pending_epoch;
    uint64_t last_commit_epoch;
} ActuatorBatch;

void batch_reset(ActuatorBatch *batch);
void batch_queue(ActuatorBatch *batch, const char *cell_id, uint64_t epoch);
int flush_t8(ActuatorBatch *batch, uint64_t commit_epoch);
uint64_t batch_last_commit_epoch(const ActuatorBatch *batch);
void actuator_diag(const ActuatorBatch *batch);

#endif
