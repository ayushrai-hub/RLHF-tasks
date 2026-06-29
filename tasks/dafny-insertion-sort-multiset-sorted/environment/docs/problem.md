# Problem: Prove Insertion Sort Correct

The `InsertionSort` method in `solution.dfy` must satisfy two postconditions at once.
First, when the method returns, the array must be sorted in non-decreasing order from
index 0 to `a.Length`. Second, the multiset of elements in the array must equal the
multiset of elements in the array before the call, meaning the method rearranges
elements rather than introducing or discarding any.

These two obligations are captured by the `Sorted` predicate and the `ArrayMultiset`
ghost function defined at the top of the file. The `Sorted(a, lo, hi)` predicate
holds when every pair of elements within the range `[lo, hi)` satisfies `a[i] <= a[j]`
for all `i < j`. The `ArrayMultiset(a)` function returns the multiset formed by all
elements of the array as a slice.

Your task is to add Dafny annotations — loop invariants, `decreases` clauses, and
ghost lemmas — that let the Dafny verifier confirm both postconditions are maintained
throughout the algorithm. The implementation itself is correct; it just lacks the
annotations Dafny needs to confirm it.
