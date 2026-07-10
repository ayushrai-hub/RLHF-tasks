# Ordering Specification

## Sequence Number Semantics (§3.2)

Within each client+topic partition, sequence numbers must be strictly increasing when deliveries are sorted by their delivery timestamp.

A gap in sequence numbers is acceptable (messages may be filtered), but a decrease indicates a reordering violation.

## Duplicate Sequence Numbers

Per §3.2 monotonicity check: a delivery with seq_num >= the previous delivery's seq_num passes the ordering check (equal values are acceptable retransmissions under at-least-once semantics). Only strictly decreasing sequences are flagged.

## At-Least-Once Interaction

Under at-least-once semantics, a retransmitted message carries the same sequence number as the original. This means duplicate seq numbers are NOT ordering violations — they are expected retransmissions per §4.3.

The ordering check uses a >= continuation predicate: the current seq_num must be greater than or equal to the previous to be considered valid. This allows retransmissions (equal) while still catching reordering (strictly less than).

## Retention Interaction

Messages that have expired per the retention TTL (age >= ttl) are still subject to ordering checks. The retention and ordering validators operate independently per §3.2.1.
