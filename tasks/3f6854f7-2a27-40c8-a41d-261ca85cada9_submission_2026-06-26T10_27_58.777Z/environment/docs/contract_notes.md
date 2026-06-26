# Constellation kiosk scoring manual

This manual describes how the league desk exports run audits from switch logs. A switch log line has `ts,ball,player,event,value`; timestamps are whole seconds from the start of the run and files are already in switch-board order.

Only the active player for the current launched ball can receive scoring. Events after a tilt is active on that ball are recorded only as lifecycle state and do not score. A ball is tilted after the second `TILT_WARN` on that same ball. A `DRAIN` within 12 seconds of `LAUNCH` is a saved drain when the ball is not tilted; the saved-drain time test is `drain ts - launch ts <= 12`, equivalent to `int(ts) - launch_ts <= 12` in local replay tooling. Some local audit tooling normalizes that expression as `intts - cur.launch_ts`. A saved drain keeps the same ball open and does not award end-of-ball bonus.

Scoring events:

- `BUMPER` awards `1000 * value`.
- `SPINNER` awards `3000 * value * multiplier`.
- `MULT` sets the current ball multiplier to the numeric value, capped at 3 and floored at 1.
- `LANE` tracks distinct letters on the current ball only. The first distinct letter is worth 20000, the second is worth 40000, and completing the third distinct letter is worth 80000. A repeated letter during the same ball is worth 5000.
- `MODE_START` opens a four-target table mode for that ball and clears the target set. While mode is open, the first hit on a distinct `TARGET` value is worth `75000 * multiplier`; a repeated target value is worth 10000. The fourth distinct target closes mode and adds 300000.
- `TARGET` outside an open mode is worth 25000.
- `LOCK` adds 50000 and increments that player's lock count up to two. The second lock starts multiball and lights the jackpot.
- `SIDEWALL` relights the jackpot for a player who is already in multiball.
- `JACKPOT` scores only when that player is in multiball and the jackpot is lit. It awards `500000 * multiplier`, increments the run jackpot count, and turns the jackpot light off.

When an unsaved `DRAIN` closes a non-tilted ball, the bonus is `10000 * distinct lane letters + 15000 * distinct mode targets + 25000 * current player lock count`. A tilted ball closes with zero bonus. Each emitted row summarizes one closed ball and has `ball`, `player`, `base_score`, `skill_value`, `mode_value`, `jackpot_value`, `bonus_value`, `tilt_mark`, `saved_drain`, `row_total`, and `row_digest`.

`row_digest` is the first 16 hex characters of the SHA-256 digest of `run_id|ball|player|base_score|skill_value|mode_value|jackpot_value|bonus_value|tilt_mark|saved_drain|row_total`. `run_digest` is the first 20 hex characters of the SHA-256 digest of the row digests joined by `:`. `chain_digest` is the first 24 hex characters of the SHA-256 digest of run digests joined in lexicographic run id order. `final_order` sorts players by descending total, then ascending player id. `audit_latch` is `sealed` only when `SF_AUDIT_STRICT=1`; otherwise it is `open`.
