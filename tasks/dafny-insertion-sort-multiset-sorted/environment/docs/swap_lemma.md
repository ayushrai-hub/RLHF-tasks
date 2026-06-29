# Swaps and Multiset Preservation

When two elements in an array are swapped, the collection of values in the array does
not change: only the positions of two values are exchanged. This makes a swap a
permutation of the array elements in the mathematical sense. Every value that was
present before the swap is still present afterward, and no new values are introduced.

In Dafny, the `multiset` of an array's contents is the most direct way to express
that two arrays contain the same elements. Two arrays have equal multisets when they
contain the same values with the same multiplicities, regardless of order. Dafny's
`multiset(s)` function converts a sequence `s` to a multiset, and array slices such
as `a[..]` can be used to form sequences for this purpose.

The challenge in a Dafny proof is that the verifier does not automatically conclude
that a swap leaves the multiset unchanged. Although the fact is obvious informally,
Dafny requires a formal argument connecting the before and after states. The
`docs/multiset_in_dafny.md` file describes Dafny's multiset syntax and operations
in more detail.
