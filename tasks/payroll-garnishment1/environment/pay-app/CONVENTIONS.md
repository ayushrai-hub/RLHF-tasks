# Conventions

- Monetary amounts and quantities are represented as whole integers rather
  than floating point values.
- Validation failures print a short status word on standard output and exit
  with a non-zero status; successful commands exit zero.
- Listings are printed in a stable, deterministic order.
- Net-pay figures are computed in integer cents through a piecewise forward
  model, and the inverse net-to-gross solve is a bisection over an integer-cent
  bracket to a stated tolerance rather than a closed-form division.
