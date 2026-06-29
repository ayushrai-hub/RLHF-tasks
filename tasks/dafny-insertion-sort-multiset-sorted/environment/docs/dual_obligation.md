# Correctness of a Sorting Algorithm

A sorting algorithm is correct when its output satisfies two independent properties.
First, the output array must be in sorted order: each element must be no greater than
the next. Second, the output must contain exactly the same elements as the input, just
rearranged. Neither property implies the other: an algorithm could produce a sorted
sequence of wrong values, or it could produce a scrambled permutation of the input
that happens not to be in order.

Multisets are the right mathematical object for expressing the second property. A
multiset is an unordered collection that tracks how many times each value appears. Two
arrays contain exactly the same elements with the same multiplicities if and only if
their multisets are equal. Dafny's built-in `multiset` type supports this equality
directly and is the standard way to express permutation in a Dafny proof.

When writing a correctness proof for a sorting method, both of these properties appear
in the postconditions, and the proof must establish each one. The loop invariants must
collectively be strong enough to imply both postconditions when the loops terminate.
