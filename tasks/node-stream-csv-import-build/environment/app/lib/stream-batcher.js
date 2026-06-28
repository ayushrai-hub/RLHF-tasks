'use strict';

const BATCH_SIZE = 1000;

async function consume(parser, onBatch) {
    let batch = [];
    let total = 0;
    for await (const row of parser) {
        batch.push(row);
        total++;
        if (batch.length >= BATCH_SIZE) {
            await onBatch(batch);
            batch = [];
        }
    }
    if (batch.length) await onBatch(batch);
    return total;
}

module.exports = { consume };
