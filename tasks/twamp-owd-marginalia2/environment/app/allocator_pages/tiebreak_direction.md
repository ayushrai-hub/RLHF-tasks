# Tiebreak direction flip

When two reflectors have an EQUAL fractional remainder in the
largest-remainder allocation, the allocator picks a winner by the
reflector's numeric suffix. The direction of that pick depends on
whether ANY reflector was observed offline this run.

## Rule

* If NO reflector was observed offline anywhere in the run:
  ASCENDING numeric suffix wins (`R2` beats `R3`, `R3` beats `R10`).
* If ANY reflector was observed offline in any cycle of the run:
  DESCENDING numeric suffix wins (`R10` beats `R3`, `R3` beats `R2`).

The flip is global: it depends on the whole run's offline state,
not on which specific reflectors are tied at that moment.

## Reflector "observed offline"

A reflector R is observed offline iff there exists at least one
cycle C in the run where R contributed zero real surviving probes
to C. The mark is the same one that drives `offline_observed = true`
in R's reflector row.

A reflector that has zero probes ANYWHERE in the run is observed
offline in every cycle and trivially triggers the flip.

## Common misimplementations

* Unconditional ASCENDING tiebreak: passes primary fixture (no
  exact remainder ties), fails alt fixture (R2 and R3 tie at
  remainder 4 and 4; descending wins R3 over R2). The primary
  fixture happens not to have an exact tie at the leftover unit;
  the alt fixture does.
* Unconditional DESCENDING tiebreak: fails any run where no
  reflector is offline and an ascending tiebreak is expected.
* Using lex order on the reflector id instead of numeric suffix:
  `R10` lex-comes before `R2` but numeric-suffix-comes AFTER
  `R2`; the tiebreak direction is on numeric suffix, not lex.

## Worked alt-fixture trace

The alt fixture has 4 reflectors `R1`, `R2`, `R3`, `R7`. R7 has zero
qualifying probes; R1 has one; R2 and R3 have four each. The
allocator computes floor allocations:

```
R1: 1 * 1000 / 9 = 111   remainder 1
R2: 4 * 1000 / 9 = 444   remainder 4
R3: 4 * 1000 / 9 = 444   remainder 4
R7: 0 * 1000 / 9 =   0   remainder 0
```

Sum of floors = 999; leftover = 1. R2 and R3 are tied at remainder
4. R7 has zero qualifying probes in EVERY cycle, so it is observed
offline; the tiebreak direction flips to DESCENDING. R3 (numeric
suffix 3) wins over R2 (numeric suffix 2). The leftover unit goes
to R3.

Final allocation:

```
R1: 111
R2: 444
R3: 445   (444 floor + 1 leftover)
R7:   0
```

Total: 1000.

An unconditional ascending tiebreak would award the leftover unit
to R2 instead, producing `R1=111, R2=445, R3=444, R7=0`. The alt
report digest would differ.
