package main

// Provided data model and primitives for the prefilter literal-set builder.
// DO NOT MODIFY this file. It defines the Literal/Seq types, the byte-rank
// table, and every mechanical helper used to transform a sequence. The only
// file you write is optimize.go (the Optimize method).

// ---- byte-rank table -------------------------------------------------------
//
// rank(b) returns a heuristic "rarity" score for a byte, in [0,255]. The LOWER
// the rank, the LESS likely that byte is to appear in arbitrary text. This
// table is fixed and must be used as-is.
var byteRank = [256]uint8{55, 52, 51, 50, 49, 48, 47, 46, 45, 103, 242, 66, 67, 229, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 56, 32, 31, 30, 29, 28, 255, 148, 164, 149, 136, 160, 155, 173, 221, 222, 134, 122, 232, 202, 215, 224, 208, 220, 204, 187, 183, 179, 177, 168, 178, 200, 226, 195, 154, 184, 174, 126, 120, 191, 157, 194, 170, 189, 162, 161, 150, 193, 142, 137, 171, 176, 185, 167, 186, 112, 175, 192, 188, 156, 140, 143, 123, 133, 128, 147, 138, 146, 114, 223, 151, 249, 216, 238, 236, 253, 227, 218, 230, 247, 135, 180, 241, 233, 246, 244, 231, 139, 245, 243, 251, 235, 201, 196, 240, 214, 152, 182, 205, 181, 127, 27, 212, 211, 210, 213, 228, 197, 169, 159, 131, 172, 105, 80, 98, 96, 97, 81, 207, 145, 116, 115, 144, 130, 153, 121, 107, 132, 109, 110, 124, 111, 82, 108, 118, 141, 113, 129, 119, 125, 165, 117, 92, 106, 83, 72, 99, 93, 65, 79, 166, 237, 163, 199, 190, 225, 209, 203, 198, 217, 219, 206, 234, 248, 158, 239, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255}

func rank(b byte) uint8 { return byteRank[b] }

// ---- data model ------------------------------------------------------------

// Literal is a byte string tagged "exact" or not. An exact literal is one that
// has not been trimmed; an inexact literal is a fragment (a prefix that may be
// followed by more bytes in a real match).
type Literal struct {
	Bytes []byte
	Exact bool
}

// Seq is a set of candidate literals in preference order (leftmost = highest
// preference). A Seq is either FINITE (Finite==true, holding an ordered list,
// possibly empty) or INFINITE (Finite==false), which means "no useful literal
// set" -- a prefilter cannot help and every position is a potential match.
type Seq struct {
	Finite bool
	Lits   []Literal
}

func (l *Literal) len() int      { return len(l.Bytes) }
func (l *Literal) isEmpty() bool { return len(l.Bytes) == 0 }
func (l *Literal) makeInexact()  { l.Exact = false }

// keepFirstBytes trims a literal to its first n bytes. If the literal already
// has n or fewer bytes it is unchanged; otherwise it is truncated AND marked
// inexact (it is now only a fragment).
func (l *Literal) keepFirstBytes(n int) {
	if n >= l.len() {
		return
	}
	l.makeInexact()
	l.Bytes = l.Bytes[:n:n]
}

// isPoisonous reports whether a literal is believed to match so frequently that
// it is worthless as a prefilter: an empty literal, or a single byte whose rank
// is very high (>= 250, i.e. very common).
func (l *Literal) isPoisonous() bool {
	return l.isEmpty() || (l.len() == 1 && rank(l.Bytes[0]) >= 250)
}

func (s *Seq) makeInfinite() {
	s.Finite = false
	s.Lits = nil
}

// length returns (count, true) for a finite Seq, or (0, false) if infinite.
func (s *Seq) length() (int, bool) {
	if !s.Finite {
		return 0, false
	}
	return len(s.Lits), true
}

func (s *Seq) isFinite() bool { return s.Finite }

// isExact reports whether the Seq is finite and every literal in it is exact.
// (An empty finite Seq is exact.)
func (s *Seq) isExact() bool {
	if !s.Finite {
		return false
	}
	for i := range s.Lits {
		if !s.Lits[i].Exact {
			return false
		}
	}
	return true
}

// minLiteralLen returns (min length, true), or (0, false) if the Seq is
// infinite or has no literals.
func (s *Seq) minLiteralLen() (int, bool) {
	if !s.Finite || len(s.Lits) == 0 {
		return 0, false
	}
	m := s.Lits[0].len()
	for i := 1; i < len(s.Lits); i++ {
		if s.Lits[i].len() < m {
			m = s.Lits[i].len()
		}
	}
	return m, true
}

// clone returns a deep copy of the Seq.
func (s *Seq) clone() Seq {
	if !s.Finite {
		return Seq{Finite: false}
	}
	out := Seq{Finite: true, Lits: make([]Literal, len(s.Lits))}
	for i := range s.Lits {
		b := make([]byte, len(s.Lits[i].Bytes))
		copy(b, s.Lits[i].Bytes)
		out.Lits[i] = Literal{Bytes: b, Exact: s.Lits[i].Exact}
	}
	return out
}

// keepFirstBytes trims every literal in the Seq to its first n bytes.
func (s *Seq) keepFirstBytes(n int) {
	if !s.Finite {
		return
	}
	for i := range s.Lits {
		s.Lits[i].keepFirstBytes(n)
	}
}

// longestCommonPrefix returns (prefix, true) -- the longest byte prefix shared
// by every literal in the Seq (possibly empty) -- or (nil, false) if the Seq is
// infinite or has no literals.
func (s *Seq) longestCommonPrefix() ([]byte, bool) {
	if !s.Finite || len(s.Lits) == 0 {
		return nil, false
	}
	base := s.Lits[0].Bytes
	n := len(base)
	for i := 1; i < len(s.Lits); i++ {
		m := s.Lits[i].Bytes
		cnt := 0
		lim := n
		if len(m) < lim {
			lim = len(m)
		}
		for cnt < lim && m[cnt] == base[cnt] {
			cnt++
		}
		n = cnt
		if n == 0 {
			return []byte{}, true
		}
	}
	return base[:n], true
}

// dedup collapses runs of CONSECUTIVE literals with identical bytes into a
// single literal. Within a collapsed run, if the exact flags disagree, the
// survivor is made inexact.
func (s *Seq) dedup() {
	if !s.Finite || len(s.Lits) == 0 {
		return
	}
	lits := s.Lits
	nextWrite := 1
	for nextRead := 1; nextRead < len(lits); nextRead++ {
		prev := nextWrite - 1
		if bytesEqual(lits[nextRead].Bytes, lits[prev].Bytes) {
			if lits[nextRead].Exact != lits[prev].Exact {
				lits[nextRead].makeInexact()
				lits[prev].makeInexact()
			}
			continue
		}
		if nextRead != nextWrite {
			lits[nextWrite] = lits[nextRead]
		}
		nextWrite++
	}
	s.Lits = lits[:nextWrite]
}

func bytesEqual(a, b []byte) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

// ---- preference minimization ----------------------------------------------
//
// minimize keeps only the literals that can still match under a leftmost-first
// (preference-order) search: a literal is dropped if some earlier retained
// literal is a prefix of it (equal literals and the empty literal count as
// prefixes). Order and each retained literal's exact flag are preserved. This
// also removes duplicates.

type trieState struct {
	trans []trieTrans // sorted by byte
}
type trieTrans struct {
	b   byte
	sid int
}
type prefTrie struct {
	states  []trieState
	matches []int // 0 == not a match; else a nonzero literal index
	nextIdx int
}

func (t *prefTrie) createState() int {
	id := len(t.states)
	t.states = append(t.states, trieState{})
	t.matches = append(t.matches, 0)
	return id
}

func (t *prefTrie) root() int {
	if len(t.states) != 0 {
		return 0
	}
	return t.createState()
}

func trieSearch(ts []trieTrans, b byte) (int, bool) {
	lo, hi := 0, len(ts)
	for lo < hi {
		mid := (lo + hi) / 2
		if ts[mid].b < b {
			lo = mid + 1
		} else if ts[mid].b > b {
			hi = mid
		} else {
			return mid, true
		}
	}
	return lo, false
}

func (t *prefTrie) insert(bytes []byte) bool {
	prev := t.root()
	if t.matches[prev] != 0 {
		return false
	}
	for _, b := range bytes {
		i, found := trieSearch(t.states[prev].trans, b)
		if found {
			prev = t.states[prev].trans[i].sid
			if t.matches[prev] != 0 {
				return false
			}
		} else {
			next := t.createState()
			tr := t.states[prev].trans
			tr = append(tr, trieTrans{})
			copy(tr[i+1:], tr[i:])
			tr[i] = trieTrans{b: b, sid: next}
			t.states[prev].trans = tr
			prev = next
		}
	}
	idx := t.nextIdx
	t.nextIdx++
	t.matches[prev] = idx
	return true
}

func minimizeLits(lits []Literal) []Literal {
	t := &prefTrie{nextIdx: 1}
	out := lits[:0]
	for i := range lits {
		if t.insert(lits[i].Bytes) {
			out = append(out, lits[i])
		}
	}
	return out
}

// minimize applies preference minimization in place.
func (s *Seq) minimize() {
	if !s.Finite {
		return
	}
	s.Lits = minimizeLits(s.Lits)
}
