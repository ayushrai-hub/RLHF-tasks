Next stage of the statkit library at `/app`. The incomplete gamma work from before should stay intact.

Now fill in the beta side. Implement the regularized incomplete beta function `sk_betai` in `/app/src/incbeta.c`, then the distribution CDFs that build on it: `sk_tdist_cdf` / `sk_tdist_sf` in `/app/src/student.c` and `sk_fdist_cdf` in `/app/src/fdist.c`. Definitions and the t/F-to-incomplete-beta relationships are in `/app/docs/ALGORITHMS.md`. Note the degrees of freedom are doubles — the t CDF has to work for non-integer `nu`.

The frozen checks for this stage are `/app/tests/test_incbeta.c` and `/app/tests/test_tdist_fdist.c`. Build from `/app` with `make`. Leave the headers, `/app/tests`, and `/app/data` alone, and keep `statctl` stubbed — that's the last stage.
