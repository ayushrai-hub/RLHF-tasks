# Held material and observation notes

## Deferred accept

Seed `pre` rows begin in internal `stashed` state until backing is up and their `stash_gen` is at or below the effective acceptance floor. `raise` sets `stash_epoch` to the current wave and snapshots barrier generation. Offered pre-lane rows are created in `stashed` with `stash_gen` equal to their wave and are not seed-origin; they require partial-cycle witness recording and a matching carry stamp before promotion even when `stash_gen` is at or below the acceptance floor.

## Seal epoch and witness ledger

Each partial cycle advances seal epoch and appends witnessed deferrals for held stashed rows into `defer-witness.bin`. Witness recording for offered rows requires a carry stamp whose barrier generation is at or below the seal epoch active during that partial cycle. Witness entries must round-trip through partial-cycle reload and warm reconciliation.

## Carry stamp ledger

See `carry-notes.md`. Carry stamps persist in `defer-carry.tab` and reload during warm reconciliation together with checkpoint session fields and the witness ledger.

## Partial cycle replay

After a partial cycle, durable row material is replayed and merged without dropping prior `sent` history, `stash_gen` markers, carry stamps, barrier generation, or dispatch journal continuity. Stash epoch, seal epoch, barrier generation, witness material, and carry stamps must survive restart through checkpoint, carry tab, and witness ledger coordination.

Recovery anchor material is part of this coordination. It must not invent witness quorum for rows that never crossed a partial cycle, but it must preserve quorum and sent state when primary carry, witness, checkpoint, or durable files are missing or stale.

## Sweep again

When observation files already exist, `sweep --again` republishes the converged view without changing outcomes. When observation files were cleared externally, `--again` must still regenerate both products to match the prior converged row states and dispatch steps.
