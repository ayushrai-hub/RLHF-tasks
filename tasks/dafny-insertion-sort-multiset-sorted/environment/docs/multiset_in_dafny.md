# Multisets in Dafny

Dafny has a built-in `multiset<T>` type that represents a collection of elements where
each element has a multiplicity (count). Unlike a set, a multiset can contain duplicate
elements. Unlike a sequence, a multiset has no ordering.

To convert a sequence `s` to a multiset, write `multiset(s)`. For an array `a`, you
typically work with the slice `a[..]` which is a sequence of all elements, so the
multiset of an array is `multiset(a[..])`.

Multiset equality in Dafny is written with `==` and means both multisets contain
exactly the same elements with the same multiplicities. For example,
`multiset([1, 2, 1]) == multiset([2, 1, 1])` is true.

Dafny supports multiset operations: union (`+`), difference (`-`), intersection (`*`),
and membership (`in`). You can also write `multiset{x}` for a singleton multiset
containing just `x`.

The `old()` expression in postconditions and invariants captures the value of an
expression at method entry. So `old(ArrayMultiset(a))` means the multiset of the
array as it was when `InsertionSort` was first called, before any modifications.
