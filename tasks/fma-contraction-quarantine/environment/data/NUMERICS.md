# Numerical background

geokern is double precision throughout and was written against round-to-nearest
IEEE-754 semantics. The strict profile preserves those semantics exactly: every
add, subtract, multiply, and divide rounds once, in source order, and signed
zero and the non-finite values keep their meaning.

The release profile relaxes that model for speed. It lets the compiler fuse a
multiply and an add into one rounding, reassociate chains of additions and
subtractions, turn a division into a multiply by a reciprocal, treat positive
and negative zero as interchangeable, and assume no operand is ever a NaN or an
infinity.

The contracts in CONTRACTS.md are stated for the strict model. A kernel whose
release output still satisfies its contract is fine to ship aggressively; one
whose release output leaves its contract is not.
