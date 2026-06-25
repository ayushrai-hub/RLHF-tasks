# Worked digest example

A tiny synthetic three-probe report so you can byte-check the recipe
in `canonical_bytes.md`. The ids and counts here are NOT drawn from
the shipped fixture; they are a minimal illustration.

## Synthetic input

Suppose the probe ledger has three rows in final output order:

```
EX-1|R1|WITHIN_BOUNDS|100
EX-2|R2|OWD_ANOMALY|900
EX-3|R3|WITHIN_BOUNDS|150
```

and the reflector ledger has three rows in final output order:

```
R1=400
R2=300
R3=300
```

and the summary tail names `total_probes=3, aligned_good=2, cycles=1`.

## Canonical byte sequence

The exact bytes that feed SHA-256 (the `\n` markers below are literal
newlines, never `\r\n`):

```
EX-1|R1|WITHIN_BOUNDS|100
EX-2|R2|OWD_ANOMALY|900
EX-3|R3|WITHIN_BOUNDS|150
##
R1=400|R2=300|R3=300
##
summary:total=3;good=2;cycles=1
```

with a final trailing `\n` after the summary line.

The two `##` markers are each a single line containing exactly the
two-byte string `##`, surrounded by `\n` on both sides.

## Verifier-side spot check

A quick way to verify your recipe matches:

```
printf 'EX-1|R1|WITHIN_BOUNDS|100\nEX-2|R2|OWD_ANOMALY|900\nEX-3|R3|WITHIN_BOUNDS|150\n##\nR1=400|R2=300|R3=300\n##\nsummary:total=3;good=2;cycles=1\n' | sha256sum
```

Any deviation in the byte recipe changes the hash. If your run's
`report_digest` differs from the verifier's expected, walk back
through the byte sequence above and identify which line differs.

See `../run_recipe/build_targets.md` for `make verify`, which prints
the run's actual `report_digest` and the per-cycle threshold ladder
so you can iterate quickly.
