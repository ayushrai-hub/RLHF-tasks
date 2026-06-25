# Refill anchor and sequence ticks

Token refill accrues on every run that executes the admit stage, including idle runs with no consume. The refill anchor (`state.last_refill_seq`) records the meta.seq value observed after the most recent refill application.

## Delta rule

When computing refill credit for the current run, count every meta.seq step from the prior anchor through the current meta.seq **inclusively**. If the anchor was set to 4 on the previous run and the current run advances meta.seq to 5, the elapsed gap is one tick and backends with a positive refill_rate receive one refill increment.

Do not exclude the current run's seq increment from the gap. A consume run that advances seq must accrue refill credit for that same tick before consume deducts tokens.

## Anchor updates

After refill applies on a run, set `state.last_refill_seq` to the current meta.seq.

Config transitions (immediate reload or replay_pending apply) align the anchor to the current meta.seq on that same run so ticks before the transition do not accrue refill across the boundary.

fresh_start in milestone 2 anchors refill without applying cross-scope accumulation per deferred-reload.md.
