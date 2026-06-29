# Combining Sorted Segments

Two adjacent sorted sequences do not necessarily form a sorted sequence when
concatenated. For example, `[1, 3]` is sorted and `[2, 5]` is sorted, but
`[1, 3, 2, 5]` is not sorted. Knowing that each segment is internally sorted says
nothing about the relationship between the last element of the first segment and the
first element of the second segment.

Dafny's `Sorted` predicate checks a specific contiguous range of an array. When
reasoning about a combined range, Dafny does not automatically merge sortedness
facts about two adjacent sub-ranges into a fact about their union. The proof
must carry enough information in its invariants for Dafny's verifier to discharge
the combined sortedness obligation at the point where it is needed.
