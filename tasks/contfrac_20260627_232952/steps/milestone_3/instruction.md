Add the continued fraction of square roots and the Pell equation. For a non-square `n`, the continued fraction of `√n` is periodic and is generated with the standard recurrence `m₀=0, d₀=1, a₀=⌊√n⌋`, then `m_{i+1}=d_i·a_i−m_i`, `d_{i+1}=(n−m_{i+1}²)/d_i`, `a_{i+1}=⌊(a₀+m_{i+1})/d_{i+1}⌋`; the period ends at the first term equal to `2·a₀`. For a perfect square, `√n = [⌊√n⌋]` with no periodic part.

- `SQRTCF <n> <k>` — print the first `k` terms of the continued fraction of `√n` (for a perfect square, just the single term `⌊√n⌋`).
- `PERIOD <n>` — print the period length of the continued fraction of `√n` (`0` for a perfect square).
- `PELL <n>` — print the fundamental solution `x y` to `x² − n·y² = 1` (found from the convergents of `√n`), or `none` if `n` is a perfect square.

Errors: `n < 1` or `k < 1` prints `ERROR: range`; a non-integer argument prints `ERROR: parse`; `ERROR: usage` / `ERROR: unknown command` apply as before.
