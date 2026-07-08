# gatectl sweep and cycle contracts

## Command warm phase

Every mutating command reloads held row material from durable storage, session metadata from checkpoint material, defer witness ledger state, and defer carry stamps before its body runs. Warm must restore wave, slot, gate flag, backing flag, stash epoch, seal epoch, barrier generation, witness ledger, carry stamps, row table, and dispatch journal entries together.

If primary checkpoint or ledger files are missing or older than the recovery anchor, warm reload reconciles from the anchor rather than downgrading already-sent rows or losing journal slots. Durable rows may be behind checkpoint material after an interrupted cast; sent state and dispatch identity still come from the newest coherent view.

## Sweep phases

When backing is up, a reconciliation sweep runs warm, accept, pick, fire, mark, and cast phases in order. Accept promotes eligible internal rows from `stashed` to `wait` using stash epoch, seal epoch, barrier generation, seed-origin markers, witness ledger eligibility, and carry stamp quorum. Pick chooses waiting rows using runtime lane order, weight, tag, and wave tie-breaks. Fire applies dispatch steps to the session table and appends journal entries without duplicating prior `(tag, wave)` fires. Mark derives observation products from the session table and journal. Cast persists durable rows, checkpoint session fields, carry stamps, and witness ledger material.

`sweep --again` republishes observation products from held session state without rerunning accept, pick, or fire.

## Cycle reload phases

`cycle --partial` writes durable rows and carry stamps, updates the witness ledger, skips checkpoint emission, then rebuilds memory through fold, vault startup, witness merge, carry merge, journal fusion, and mark.

Full cycles also cast checkpoint material including stash epoch, seal epoch, barrier generation, and the dispatch journal.

## Dispatch identity

Dispatch steps are keyed by `tag` and `wave`. Slot numbers increase monotonically within a workspace and resume from the last persisted slot after warm reload. Pick ordering follows `dispatch.lane_order` in `/app/environment/runtime/dispatch.toml`, then ascending weight, tag, and wave.

Repeated tags across offers are valid. They must produce separate row observations and separate dispatch entries when their waves differ.

## Observation visibility

Row observation states are `wait`, `sent`, and `gone`. Internal `stashed` rows are reported as `wait` until dispatched. Completed handoffs are reported as `sent` regardless of lane.

## Observation products

`row-obs.jsonl` rows use `tag`, `lane`, `state`, and `wave`. `dispatch-obs.jsonl` rows use `tag`, `wave`, `phase`, and `slot`.
