Add convergents — the successive rational approximations obtained by truncating the continued fraction. Using the terms `a_i`, the convergents `h_i / k_i` follow the recurrence `h_i = a_i·h_{i-1} + h_{i-2}`, `k_i = a_i·k_{i-1} + k_{i-2}` (with `h_{-1}=1, h_{-2}=0, k_{-1}=0, k_{-2}=1`); each is already in lowest terms.

- `CONVERGENT <p> <q> <k>` — print the `k`-th convergent (0-indexed) of `p/q` as a reduced fraction.
- `CONVERGENTS <p> <q>` — print all convergents of `p/q` in order, space-separated.

Errors: `q <= 0` prints `ERROR: range`; a `k` outside `0..(#terms − 1)` prints `ERROR: range`; a non-integer argument prints `ERROR: parse`; `ERROR: usage` / `ERROR: unknown command` apply as before.
