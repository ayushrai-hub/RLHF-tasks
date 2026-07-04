package main

// Optimize turns this sequence of candidate prefix literals into the final
// prefilter literal set, in place, exactly as the reference tool does.
//
// This is the ONLY file you may modify. Everything the transformation needs is
// already provided in litpre.go: the Literal/Seq types, the byte-rank table
// (rank), and the mechanical primitives -- minimize, longestCommonPrefix,
// keepFirstBytes, dedup, isPoisonous, clone, makeInfinite, isExact, isFinite,
// minLiteralLen, length. Compose them into the reference's rule.
//
// The current implementation is a stub that leaves the sequence unchanged.
// Replace it. Study the worked input -> output pairs in /app/examples to
// reconstruct the exact rule; it is not written down here.
func (s *Seq) Optimize() {
	// TODO: implement.
}
