Next stage of the statkit library at `/app`. The chi-square, t, and F CDFs from before should stay intact.

Now add the quantile functions — the inverses of the CDFs. Implement `sk_chisq_ppf` and `sk_tdist_ppf` in `/app/src/invdist.c` so that for a probability p in (0,1) each returns the value whose CDF equals p. Definitions and the accuracy target are in `/app/docs/ALGORITHMS.md`; degrees of freedom can be non-integer and out-of-range inputs should return NaN.

The frozen check for this stage is `/app/tests/test_invdist.c`. Build from `/app` with `make`. Leave the headers, `/app/tests`, and `/app/data` alone, and keep `statctl` stubbed — the CLI is the last stage.
