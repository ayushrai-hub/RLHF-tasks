#!/bin/bash
set -euo pipefail
# Oracle: reproduce the reference prefilter literal-set optimization. Self-contained:
# writes the full Optimize method into /app/optimize.go and builds. Does not depend
# on any sibling script; litpre.go, main.go and parse.go are left untouched.
if [ ! -d /app ] || [ ! -f /app/main.go ]; then
  echo "expected the Go project in /app" >&2
  exit 1
fi
cd /app
cat > /app/optimize.go <<'GOEOF'
package main

// ORACLE: the reference prefilter literal-set optimization.
//
// Working over the literals as PREFIXES in preference order:
//  1. If the sequence is infinite, or (after remembering the original count)
//     any literal is empty, give up (empty => a match everywhere).
//  2. Preference-minimize (drop literals a retained earlier literal is a prefix
//     of; also dedups).
//  3. If the literals share a common prefix:
//       a. memchr shortcut -- if there was originally more than one literal and
//          the common prefix is 1..3 bytes long and its first byte is rare
//          (rank < 200), collapse everything to just that single rare byte.
//       b. otherwise, if the common prefix is "worth it" -- longer than 4 bytes,
//          or longer than 1 byte when the set isn't already a small exact set
//          (exact with <= 16 literals) -- collapse every literal to that common
//          prefix.
//  4. Remember the sequence if it is still exact (a fallback).
//  5. Shrink an over-long set: for (keep,limit) in (5,10),(4,10),(3,64),(2,64),
//     (1,10), stop at the first whose limit >= the current count; otherwise trim
//     every literal to `keep` bytes and re-minimize.
//  6. If any literal is now poisonous, give up (go infinite).
//  7. If we had saved an exact fallback, revert to it when the optimized set is
//     infinite, or its shortest literal is <= 2 bytes, or it now has > 64
//     literals.
func (s *Seq) Optimize() {
	origlen, ok := s.length()
	if !ok {
		return
	}
	if mll, has := s.minLiteralLen(); has && mll == 0 {
		s.makeInfinite()
		return
	}
	s.minimize()

	if fix, hasFix := s.longestCommonPrefix(); hasFix {
		if origlen > 1 && len(fix) >= 1 && len(fix) <= 3 && rank(fix[0]) < 200 {
			s.keepFirstBytes(1)
			s.dedup()
			return
		}
		l, _ := s.length()
		isfast := s.isExact() && l <= 16
		usefix := len(fix) > 4 || (len(fix) > 1 && !isfast)
		if usefix {
			s.keepFirstBytes(len(fix))
			s.dedup()
		}
	}

	var exact *Seq
	if s.isExact() {
		c := s.clone()
		exact = &c
	}

	attempts := [5][2]int{{5, 10}, {4, 10}, {3, 64}, {2, 64}, {1, 10}}
	for _, kl := range attempts {
		keep, limit := kl[0], kl[1]
		l, ok := s.length()
		if !ok || l <= limit {
			break
		}
		s.keepFirstBytes(keep)
		s.minimize()
	}

	if s.Finite {
		for i := range s.Lits {
			if s.Lits[i].isPoisonous() {
				s.makeInfinite()
				break
			}
		}
	}

	if exact != nil {
		if !s.isFinite() {
			*s = *exact
			return
		}
		if mll, has := s.minLiteralLen(); !has || mll <= 2 {
			*s = *exact
			return
		}
		if l, ok := s.length(); !ok || l > 64 {
			*s = *exact
			return
		}
	}
}
GOEOF
go build -o /tmp/litpre .
echo "build OK"
