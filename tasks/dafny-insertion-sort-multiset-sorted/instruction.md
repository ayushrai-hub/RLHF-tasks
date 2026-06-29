# Prove Insertion Sort Correct in Dafny

Your task is to make `dafny verify /app/solution.dfy` exit with code 0. The file already contains a complete insertion sort implementation in Dafny with a fixed specification. The method `InsertionSort` has two postconditions: the output array must be sorted in non-decreasing order, and it must contain exactly the same elements as the input expressed as multiset equality. Both must hold simultaneously; the verifier checks both.

Supply the missing loop invariants, termination measures, and any ghost lemmas needed to discharge the proof obligations. You may add ghost lemmas anywhere in the file above or below the spec region. You may not modify any predicate definition, method signature, `requires`, or `ensures` clause; those are frozen. Do not use `assume`, `{:axiom}`, `{:verify false}`, or `{:extern}`.

See `docs/` for relevant Dafny language references. Run `bash /app/verify.sh` to check your proof; run `bash /app/run.sh` to execute the method on sample inputs without verification.
