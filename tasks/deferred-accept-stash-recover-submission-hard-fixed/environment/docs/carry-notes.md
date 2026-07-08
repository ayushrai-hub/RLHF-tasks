# Deferred carry stamps

## Offer carry ledger

Each `offer` records a carry stamp in `<workroot>/.state/defer-carry.tab` as `tag|wave|barrier_gen`. The barrier generation is the seal epoch active when the offer was staged. Carry stamps must round-trip through warm reload and partial-cycle replay.

## Coupling with witness ledger

Partial cycles advance seal epoch and append witnessed deferrals for held stashed rows into `defer-witness.bin`. A non-seed offer is witnessed only when a matching carry stamp exists with `barrier_gen` at or below the seal epoch active during that partial cycle. Witness entries alone are not sufficient for offered rows.

## Barrier generation on raise

`raise` snapshots barrier generation from the current seal epoch when seal epoch is active, otherwise from the stash epoch set during raise. Acceptance eligibility for offered rows consults barrier generation, carry stamps, witness ledger entries, and the effective acceptance floor together.

## Effective acceptance floor

The effective acceptance floor is `stash_epoch`. Seal epoch does not lower it. Seed-origin rows follow the floor alone. Offered rows require witness and carry quorum in addition to the floor.

## Partial cycle replay

After a partial cycle, durable row material, carry stamps, witness ledger, barrier generation, stash epoch, seal epoch, and dispatch journal continuity must survive restart through coordinated checkpoint, carry tab, and witness ledger reload.

## Sweep again

When observation files were cleared externally, `sweep --again` must regenerate both products from held session state without rerunning accept, pick, or fire. Clearing `defer-carry.tab` or `defer-witness.bin` before `--again` still requires the converged view to be reproduced from remaining persisted material.
