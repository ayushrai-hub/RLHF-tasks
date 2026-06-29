# The Sorted Predicate

The `Sorted` predicate is defined over a half-open range `[lo, hi)` of an array. It
holds when for every pair of indices `i` and `j` within the range, if `i < j` then
`a[i] <= a[j]`. This is the standard definition of non-decreasing order.

The range parameters make it possible to express partial sortedness: `Sorted(a, 0, k)`
means only the first `k` elements are sorted, without making any claim about elements
at index `k` and beyond. This is essential for stating loop invariants for sorting
algorithms, which typically sort progressively larger prefixes or suffixes.

A key property of `Sorted` is that it is vacuously true for empty ranges and
singleton ranges. `Sorted(a, i, i)` and `Sorted(a, i, i+1)` are both trivially true
for any valid `i`.

When combining two adjacent sorted ranges, knowing `Sorted(a, 0, j)` and
`Sorted(a, j, k)` does not by itself imply `Sorted(a, 0, k)`. Proving
combined-range sortedness may require stating relationships that go beyond
sortedness of each individual part.
