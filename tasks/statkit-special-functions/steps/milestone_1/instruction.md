I've got a small C stats library at `/app` called statkit. It's meant to do classical hypothesis testing (chi-square, t, F) with no dependencies beyond libm, but the numerically tricky pieces were never filled in — they're stubbed out and `make test` fails.

The whole thing is built in three stages and I'll hand them to you one at a time. Start with the foundation: the regularized incomplete gamma functions and the chi-square CDF that sits on top of them.

Implement `sk_gammap` and `sk_gammaq` in `/app/src/incgamma.c`, and `sk_chisq_cdf` / `sk_chisq_sf` in `/app/src/chisq.c`. The exact definitions and the relationship between chi-square and incomplete gamma are in `/app/docs/ALGORITHMS.md`; the frozen acceptance checks for this stage are `/app/tests/test_incgamma.c` and `/app/tests/test_chisq.c`. Build with `make` from `/app` and accuracy should be near double precision across the usable range.

Don't touch the public headers in `/app/include`, the files under `/app/tests`, or the sample inputs in `/app/data`. The incomplete-beta, Student-t, F, and `statctl` pieces stay stubbed for now — they're later stages, and their tests will still fail until then.
