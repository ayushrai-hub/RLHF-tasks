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
	pre                 string // empty = release
}

func parseSemver(s string) semver {
	pre := ""
	base := s
	if idx := strings.Index(s, "-"); idx != -1 {
		base = s[:idx]
		pre = s[idx+1:]
	}
	parts := strings.Split(base, ".")
	maj, _ := strconv.Atoi(parts[0])
	min, _ := strconv.Atoi(parts[1])
	pat, _ := strconv.Atoi(parts[2])
	return semver{maj, min, pat, pre}
}

func (v semver) String() string {
	s := fmt.Sprintf("%d.%d.%d", v.major, v.minor, v.patch)
	if v.pre != "" {
		s += "-" + v.pre
	}
	return s
}

func (v semver) isPrerelease() bool { return v.pre != "" }

func (v semver) less(o semver) bool {
	if v.major != o.major { return v.major < o.major }
	if v.minor != o.minor { return v.minor < o.minor }
	if v.patch != o.patch { return v.patch < o.patch }
	// pre-release sorts below release
	if v.pre == "" && o.pre == "" { return false }
	if v.pre == "" { return false } // release > pre
	if o.pre == "" { return true }  // pre < release
	return v.pre < o.pre
}

func (v semver) gte(o semver) bool { return !v.less(o) }
func (v semver) lt(o semver) bool  { return v.less(o) }
func (v semver) eq(o semver) bool {
	return v.major == o.major && v.minor == o.minor && v.patch == o.patch && v.pre == o.pre
}

type constraint struct {
	raw string
}

func (c constraint) hasPre() bool {
	// constraint references a pre-release if the version part contains -
	s := c.raw
	s = strings.TrimPrefix(s, "^")
	s = strings.TrimPrefix(s, "~")
	s = strings.TrimPrefix(s, ">=")
	s = strings.TrimPrefix(s, "<")
	s = strings.TrimSpace(s)
	return strings.Contains(s, "-")
}

func (c constraint) matches(v semver) bool {
	// if constraint has no pre-release tag, skip pre-release versions
	if v.isPrerelease() && !c.hasPre() {
		return false
	}

	s := c.raw
	if strings.HasPrefix(s, "^") {
		base := parseSemver(s[1:])
		return v.major == base.major && v.gte(base)
	}
	if strings.HasPrefix(s, "~") {
		base := parseSemver(s[1:])
		return v.major == base.major && v.minor == base.minor && v.gte(base)
	}
	if strings.HasPrefix(s, ">=") && strings.Contains(s, " <") {
		parts := strings.SplitN(s, " ", 2)
		lo := parseSemver(parts[0][2:])
		hi := parseSemver(strings.TrimPrefix(parts[1], "<"))
		return v.gte(lo) && v.lt(hi)
	}
	if strings.HasPrefix(s, ">=") {
		base := parseSemver(s[2:])
		return v.gte(base)
	}
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

var registry = map[string][]*pkgVersion{}
var requirements []dep
var locks = map[string]semver{}

func getVersions(pkg string, includeYanked bool) []semver {
	var vs []semver
	for _, pv := range registry[pkg] {
		if !includeYanked && pv.yanked { continue }
		vs = append(vs, pv.version)
	}
	sort.Slice(vs, func(i, j int) bool { return vs[j].less(vs[i]) })
	return vs
}

func getPkgVersion(pkg string, v semver) *pkgVersion {
	for _, pv := range registry[pkg] {
		if pv.version.eq(v) { return pv }
	}
	return nil
}

func resolve() (map[string]semver, bool, string) {
	needed := map[string][]constraint{}
	for _, r := range requirements {
		needed[r.pkg] = append(needed[r.pkg], r.constraint)
	}

	resolved := map[string]semver{}
	for pkg, v := range locks {
		resolved[pkg] = v
	}

	maxIter := 200
	tried := map[string]map[string]bool{}
	for iter := 0; iter < maxIter; iter++ {
		progress := false
		var conflictPkg, conflictConstr string
		allDone := true

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

		violation := false
		for pkg, v := range resolved {
			if pkg == "" { continue }
			for _, c := range needed[pkg] {
				if !c.matches(v) {
					if tried[pkg] == nil { tried[pkg] = map[string]bool{} }
					tried[pkg][v.String()] = true
					delete(resolved, pkg)
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
