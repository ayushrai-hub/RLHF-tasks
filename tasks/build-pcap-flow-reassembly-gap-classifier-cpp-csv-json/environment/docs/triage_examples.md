# Triage Examples

Common cases:

- A packet starts exactly at the current frontier: in order.
- A packet starts beyond the frontier: a gap has been observed.
- A later packet reaches the missing bytes: the previously observed gap can become filled.
- A repeated interval entirely behind the frontier: retransmit.
- A packet starts behind the frontier but extends beyond it: overlap.
