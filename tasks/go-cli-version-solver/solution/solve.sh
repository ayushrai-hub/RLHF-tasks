#!/bin/bash
set -euo pipefail

cat > /app/solver.go << 'EOF'
package main

import (
	"bufio"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
)

type semver struct {
	major, minor, patch int
}

func parseSemver(s string) semver {
	parts := strings.Split(s, ".")
	maj, _ := strconv.Atoi(parts[0])
	min, _ := strconv.Atoi(parts[1])
	pat, _ := strconv.Atoi(parts[2])
	return semver{maj, min, pat}
}

func (v semver) String() string {
	return fmt.Sprintf("%d.%d.%d", v.major, v.minor, v.patch)
}

func (v semver) less(o semver) bool {
	if v.major != o.major { return v.major < o.major }
	if v.minor != o.minor { return v.minor < o.minor }
	return v.patch < o.patch
}

func (v semver) gte(o semver) bool { return !v.less(o) }
func (v semver) lt(o semver) bool  { return v.less(o) }
func (v semver) eq(o semver) bool  { return v.major == o.major && v.minor == o.minor && v.patch == o.patch }

type constraint struct {
	raw string
}

// matches checks if version v satisfies the constraint
func (c constraint) matches(v semver) bool {
	s := c.raw
	if strings.HasPrefix(s, "^") {
		base := parseSemver(s[1:])
		// same major, >= base
		return v.major == base.major && v.gte(base)
	}
	if strings.HasPrefix(s, "~") {
		base := parseSemver(s[1:])
		// same major.minor, >= base
		return v.major == base.major && v.minor == base.minor && v.gte(base)
	}
	if strings.HasPrefix(s, ">=") && strings.Contains(s, " <") {
		// range: >=X.Y.Z <A.B.C
		parts := strings.Split(s, " ")
		lo := parseSemver(parts[0][2:])
		hi := parseSemver(parts[1][1:])
		return v.gte(lo) && v.lt(hi)
	}
	if strings.HasPrefix(s, ">=") {
		base := parseSemver(s[2:])
		return v.gte(base)
	}
	// exact match
	base := parseSemver(s)
	return v.eq(base)
}

type dep struct {
	pkg        string
	constraint constraint
}

type pkgVersion struct {
	pkg     string
	version semver
	yanked  bool
	deps    []dep
}

var registry = map[string][]*pkgVersion{} // pkg -> versions
var requirements []dep                     // top-level ADD'd packages
var locks = map[string]semver{}            // locked versions

func getVersions(pkg string, yanked bool) []semver {
	var vs []semver
	for _, pv := range registry[pkg] {
		if !yanked && pv.yanked { continue }
		vs = append(vs, pv.version)
	}
	sort.Slice(vs, func(i, j int) bool { return vs[j].less(vs[i]) }) // descending
	return vs
}

func getPkgVersion(pkg string, v semver) *pkgVersion {
	for _, pv := range registry[pkg] {
		if pv.version.eq(v) { return pv }
	}
	return nil
}

// resolve does backtracking to find compatible version set
func resolve() (map[string]semver, bool, string) {
	type assignment struct {
		pkg string
		ver semver
	}

	// collect all top-level requirements
	needed := map[string][]constraint{}
	for _, r := range requirements {
		needed[r.pkg] = append(needed[r.pkg], r.constraint)
	}

	resolved := map[string]semver{}
	for pkg, v := range locks {
		resolved[pkg] = v
	}

	// iteratively resolve with backtracking via retrying lower versions
	maxIter := 200
	tried := map[string]map[string]bool{} // pkg -> set of tried version strings
	for iter := 0; iter < maxIter; iter++ {
		progress := false
		var conflictPkg, conflictConstr string
		allDone := true

		// process packages in sorted order for determinism
		var pkgList []string
		for pkg := range needed {
			pkgList = append(pkgList, pkg)
		}
		sort.Strings(pkgList)

		for _, pkg := range pkgList {
			constraints := needed[pkg]
			if _, ok := resolved[pkg]; ok { continue }
			allDone = false
			versions := getVersions(pkg, false)
			if tried[pkg] == nil { tried[pkg] = map[string]bool{} }
			found := false
			for _, v := range versions {
				if tried[pkg][v.String()] { continue }
				ok := true
				for _, c := range constraints {
					if !c.matches(v) { ok = false; break }
				}
				if ok {
					resolved[pkg] = v
					found = true
					progress = true
					// add deps
					pv := getPkgVersion(pkg, v)
					if pv != nil {
						for _, d := range pv.deps {
							needed[d.pkg] = append(needed[d.pkg], d.constraint)
						}
					}
					break
				}
			}
			if !found {
				conflictPkg = pkg
				conflictConstr = constraints[0].raw
			}
		}

		if allDone { break }

		// check resolved for constraint violations (diamond deps)
		violation := false
		for pkg, v := range resolved {
			if pkg == "" { continue }
			for _, c := range needed[pkg] {
				if !c.matches(v) {
					// need to backtrack: mark this version as tried, remove it
					if tried[pkg] == nil { tried[pkg] = map[string]bool{} }
					tried[pkg][v.String()] = true
					delete(resolved, pkg)
					// remove deps that were added by this package's version
					violation = true
					progress = true
					break
				}
			}
			if violation { break }
		}
		if violation { continue }

		if !progress && !allDone {
			return nil, false, fmt.Sprintf("CONFLICT %s %s", conflictPkg, conflictConstr)
		}
	}

	// final check
	for pkg, v := range resolved {
		for _, c := range needed[pkg] {
			if !c.matches(v) {
				return nil, false, fmt.Sprintf("CONFLICT %s %s", pkg, c.raw)
			}
		}
	}

	return resolved, true, ""
}

func main() {
	sc := bufio.NewScanner(os.Stdin)
	sc.Buffer(make([]byte, 1<<20), 1<<20)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" { continue }
		p := strings.Fields(line)
		switch p[0] {
		case "PUBLISH":
			pkg := p[1]
			ver := parseSemver(p[2])
			registry[pkg] = append(registry[pkg], &pkgVersion{pkg: pkg, version: ver})
			fmt.Println("OK")

		case "YANK":
			pkg := p[1]
			ver := parseSemver(p[2])
			for _, pv := range registry[pkg] {
				if pv.version.eq(ver) { pv.yanked = true }
			}
			fmt.Printf("YANKED %s %s\n", pkg, ver.String())

		case "DEPEND":
			pkg := p[1]
			ver := parseSemver(p[2])
			depPkg := p[3]
			constr := strings.Join(p[4:], " ")
			pv := getPkgVersion(pkg, ver)
			pv.deps = append(pv.deps, dep{pkg: depPkg, constraint: constraint{raw: constr}})
			fmt.Println("OK")

		case "ADD":
			pkg := p[1]
			constr := strings.Join(p[2:], " ")
			requirements = append(requirements, dep{pkg: pkg, constraint: constraint{raw: constr}})
			fmt.Println("OK")

		case "RESOLVE":
			res, ok, msg := resolve()
			if !ok {
				fmt.Println(msg)
			} else {
				fmt.Println("RESOLVED")
				var pkgs []string
				for pkg := range res { pkgs = append(pkgs, pkg) }
				sort.Strings(pkgs)
				for _, pkg := range pkgs {
					fmt.Printf("%s %s\n", pkg, res[pkg].String())
				}
			}

		case "LOCK":
			pkg := p[1]
			ver := parseSemver(p[2])
			// check if it violates existing constraints
			valid := true
			for _, r := range requirements {
				if r.pkg == pkg && !r.constraint.matches(ver) {
					valid = false
					break
				}
			}
			if !valid {
				fmt.Printf("LOCK_ERROR %s %s\n", pkg, ver.String())
			} else {
				locks[pkg] = ver
				fmt.Printf("LOCKED %s %s\n", pkg, ver.String())
			}

		case "UPGRADE":
			pkg := p[1]
			current, locked := locks[pkg]
			if !locked {
				fmt.Println("NO_UPGRADE")
				continue
			}
			// find highest compatible version
			versions := getVersions(pkg, false)
			var constraints []constraint
			for _, r := range requirements {
				if r.pkg == pkg { constraints = append(constraints, r.constraint) }
			}
			best := current
			for _, v := range versions {
				ok := true
				for _, c := range constraints {
					if !c.matches(v) { ok = false; break }
				}
				if ok && v.gte(current) && !v.eq(current) {
					best = v
					break
				}
			}
			if best.eq(current) {
				fmt.Println("NO_UPGRADE")
			} else {
				locks[pkg] = best
				fmt.Printf("UPGRADED %s %s\n", pkg, best.String())
			}

		case "UNLOCK":
			pkg := p[1]
			if _, ok := locks[pkg]; !ok {
				fmt.Printf("UNLOCK_ERROR %s\n", pkg)
			} else {
				delete(locks, pkg)
				fmt.Printf("UNLOCKED %s\n", pkg)
			}

		case "REMOVE":
			pkg := p[1]
			// remove from requirements
			var newReqs []dep
			for _, r := range requirements {
				if r.pkg != pkg { newReqs = append(newReqs, r) }
			}
			requirements = newReqs
			delete(locks, pkg)
			fmt.Printf("REMOVED %s\n", pkg)
		}
	}
}
EOF

cd /app && go build -o /app/solver /app/solver.go

# sanity check
echo "PUBLISH foo 1.0.0
PUBLISH foo 1.1.0
ADD foo ^1.0.0
RESOLVE" | /app/solver
