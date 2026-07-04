Build a Rust command-line tool for the coral galois lantern. The job is to analyze monic integer quintics exactly while staying offline and using only Rust's standard library.

The first command-line argument is an input file. Each non-empty line contains six space-separated integers, highest degree first, for a monic degree-five polynomial. For each polynomial, compute the exact discriminant, decide irreducibility over Q, and compute the pairwise-sum resolvent, the monic degree-ten polynomial formed from all sums x_i + x_j over distinct pairs of roots.

Write the output JSON array to the path in the second command-line argument, preserving input order. Every object must include polynomial, irreducible, discriminant, galois_group, solvable_by_radicals, and pair_sum_resolvent. Use decimal strings for the discriminant and the resolvent coefficients. Irreducible quintics must be labeled C5, D5, F20, A5, or S5; reducible quintics should have a null group but still need correct numeric and solvability results.

The project lives in /app and must run as cargo run --release -- <input> <output>. Keep the implementation in Rust and do not shell out to external math tools.