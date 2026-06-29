# Reconciliation Specification

## Drift Computation

Per ITU-T X.224 §8.1:
  drift = abs(expected - actual) / (stages - 1) / 1000

Normalization by (stages - 1) accounts for inter-hop accumulation.

## Threshold

Per §8.2 Note 1: strict greater-than comparison.
drift > threshold → FAIL. Packets at exactly threshold PASS.
